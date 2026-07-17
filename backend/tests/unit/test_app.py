import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.infrastructure.config import Settings, get_settings


def test_create_app_stores_settings_on_app_state(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setattr("backend.app.check_database_connection", lambda _url: None)
    monkeypatch.setattr("backend.app.sync_database_schema", lambda _url: None)
    monkeypatch.setattr("backend.app.check_redis_connection", lambda _url: None)

    app = create_app()

    assert not hasattr(app.state, "settings")

    with TestClient(app):
        assert isinstance(app.state.settings, Settings)
        assert app.state.settings.api_port == 8000
        assert app.state.settings.cors_allow_origins


def test_health_endpoint_returns_ok_when_all_deps_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.app.check_database_connection", lambda _url: None)
    monkeypatch.setattr("backend.app.sync_database_schema", lambda _url: None)
    monkeypatch.setattr("backend.app.check_redis_connection", lambda _url: None)
    check_db_conn = "backend.application.services.health_service.check_database_connection"
    check_redis_conn = "backend.application.services.health_service.check_redis_connection"
    monkeypatch.setattr(check_db_conn, lambda _url: None)
    monkeypatch.setattr(check_redis_conn, lambda _url: None)

    app = create_app()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "details": {"database": "ok", "redis": "ok"},
    }


def test_health_endpoint_returns_503_when_dep_is_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.app.check_database_connection", lambda _url: None)
    monkeypatch.setattr("backend.app.sync_database_schema", lambda _url: None)
    monkeypatch.setattr("backend.app.check_redis_connection", lambda _url: None)

    def fail_redis(_url: str) -> None:
        raise RuntimeError("redis down")

    check_db_conn = "backend.application.services.health_service.check_database_connection"
    check_redis_conn = "backend.application.services.health_service.check_redis_connection"
    monkeypatch.setattr(check_db_conn, lambda _url: None)
    monkeypatch.setattr(check_redis_conn, fail_redis)

    app = create_app()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "details": {"database": "ok", "redis": "error"},
    }


def test_create_app_fails_fast_when_database_check_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_db(_url: str) -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr("backend.app.check_database_connection", fail_db)
    monkeypatch.setattr("backend.app.sync_database_schema", lambda _url: None)
    monkeypatch.setattr("backend.app.check_redis_connection", lambda _url: None)

    app = create_app()

    with pytest.raises(RuntimeError, match="database down"):
        with TestClient(app):
            pass


def test_create_app_allows_cors_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.app.check_database_connection", lambda _url: None)
    monkeypatch.setattr("backend.app.sync_database_schema", lambda _url: None)
    monkeypatch.setattr("backend.app.check_redis_connection", lambda _url: None)

    app = create_app()

    with TestClient(app) as client:
        response = client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"
