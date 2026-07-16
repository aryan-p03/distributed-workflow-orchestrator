from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app import create_app
from backend.domain.auth import hash_password
from backend.infrastructure.config import Settings, get_settings
from backend.infrastructure.db import Base
from tests.factories import create_user


@dataclass(frozen=True)
class SeededUser:
    id: int
    email: str
    username: str
    password: str


@dataclass(frozen=True)
class AuthenticatedClient:
    client: TestClient
    user: SeededUser
    token: str

    @property
    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


class InMemoryRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def flushdb(self) -> None:
        self._store.clear()

    def set(self, key: str, value: str) -> bool:
        self._store[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0


@pytest.fixture()
def test_settings_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[Settings]:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("REDIS_URL", "redis://test-redis:6379/0")
    monkeypatch.setenv("SCHEMA_SYNC_ON_STARTUP", "false")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-that-is-at-least-32-bytes-long")
    monkeypatch.setenv("JWT_EXPIRES_SECONDS", "3600")
    get_settings.cache_clear()
    settings = get_settings()
    yield settings
    get_settings.cache_clear()


@pytest.fixture()
def db_engine(test_settings_env: Settings) -> Iterator[Engine]:
    connect_args = (
        {"check_same_thread": False} if test_settings_env.database_url.startswith("sqlite") else {}
    )
    engine = create_engine(
        test_settings_env.database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    Base.metadata.create_all(engine, checkfirst=True)
    yield engine
    Base.metadata.drop_all(engine, checkfirst=True)
    engine.dispose()


@pytest.fixture()
def session_factory(db_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def isolated_redis() -> Iterator[InMemoryRedis]:
    redis = InMemoryRedis()
    redis.flushdb()
    yield redis
    redis.flushdb()


@pytest.fixture()
def seeded_user(db_session: Session) -> SeededUser:
    password = "secret123"
    user = create_user(
        db_session,
        email="seeded@example.com",
        username="seeded",
        password_hash=hash_password(password),
    )
    db_session.commit()
    return SeededUser(id=user.id, email=user.email, username=user.username, password=password)


@pytest.fixture()
def test_client(
    test_settings_env: Settings,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setattr("backend.app.check_database_connection", lambda _url: None)
    monkeypatch.setattr("backend.app.check_redis_connection", lambda _url: None)
    monkeypatch.setattr("backend.app.sync_database_schema", lambda _url: None)

    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def authenticated_client(test_client: TestClient, seeded_user: SeededUser) -> AuthenticatedClient:
    login_response = test_client.post(
        "/auth/login",
        json={"email": seeded_user.email, "password": seeded_user.password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return AuthenticatedClient(client=test_client, user=seeded_user, token=token)
