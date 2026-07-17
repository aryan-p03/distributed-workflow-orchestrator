"""Unit tests for AuthService using an in-memory fake repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from backend.application.services.auth_service import AuthService
from backend.domain.auth import AuthError, AuthUser, TokenError, hash_password
from backend.infrastructure.repositories.user_repository import UserRepository

# ---------------------------------------------------------------------------
# In-memory fake repository
# ---------------------------------------------------------------------------


class FakeUserRepository(UserRepository):
    """Minimal in-memory stand-in; no database required."""

    def __init__(self) -> None:
        self._store: dict[UUID, AuthUser] = {}

    def get_by_id(self, user_id: UUID) -> AuthUser | None:
        return self._store.get(user_id)

    def get_by_email(self, email: str) -> AuthUser | None:
        return next((u for u in self._store.values() if u.email == email), None)

    def email_exists(self, email: str) -> bool:
        return any(u.email == email for u in self._store.values())

    def username_exists(self, username: str) -> bool:
        return any(u.username == username for u in self._store.values())

    def create(self, email: str, username: str, password_hash: str) -> AuthUser:
        user = AuthUser(
            id=uuid4(),
            email=email,
            username=username,
            password_hash=password_hash,
            created_at=datetime.now(UTC),
        )
        self._store[user.id] = user
        return user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SECRET = "test-secret-key-that-is-at-least-32-bytes-long"
_EXPIRES = 3600


@pytest.fixture()
def repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture()
def service(repo: FakeUserRepository) -> AuthService:
    return AuthService(repo=repo, jwt_secret=_SECRET, jwt_expires_seconds=_EXPIRES)


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------


def test_register_creates_user(service: AuthService, repo: FakeUserRepository) -> None:
    user = service.register("alice@example.com", "alice", "s3cr3t")

    assert user.email == "alice@example.com"
    assert user.username == "alice"
    assert repo.get_by_id(user.id) is not None


def test_register_hashes_password(service: AuthService) -> None:
    user = service.register("alice@example.com", "alice", "s3cr3t")

    assert user.password_hash != "s3cr3t"
    from backend.domain.auth import verify_password

    assert verify_password("s3cr3t", user.password_hash) is True


def test_register_duplicate_email_raises(service: AuthService) -> None:
    service.register("alice@example.com", "alice", "s3cr3t")

    with pytest.raises(AuthError, match="Email"):
        service.register("alice@example.com", "alice2", "other")


def test_register_duplicate_username_raises(service: AuthService) -> None:
    service.register("alice@example.com", "alice", "s3cr3t")

    with pytest.raises(AuthError, match="Username"):
        service.register("alice2@example.com", "alice", "other")


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


def test_login_returns_jwt_for_valid_credentials(service: AuthService) -> None:
    service.register("alice@example.com", "alice", "s3cr3t")

    token = service.login("alice@example.com", "s3cr3t")

    assert isinstance(token, str)
    assert len(token) > 0


def test_login_wrong_password_raises(service: AuthService) -> None:
    service.register("alice@example.com", "alice", "s3cr3t")

    with pytest.raises(AuthError, match="Invalid"):
        service.login("alice@example.com", "wrong")


def test_login_unknown_email_raises(service: AuthService) -> None:
    with pytest.raises(AuthError, match="Invalid"):
        service.login("nobody@example.com", "s3cr3t")


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


def test_get_current_user_returns_user_for_valid_token(service: AuthService) -> None:
    registered = service.register("alice@example.com", "alice", "s3cr3t")
    token = service.login("alice@example.com", "s3cr3t")

    current = service.get_current_user(token)

    assert current.id == registered.id
    assert current.email == "alice@example.com"


def test_get_current_user_rejects_invalid_token(service: AuthService) -> None:
    with pytest.raises(TokenError):
        service.get_current_user("not.a.valid.token")


def test_get_current_user_rejects_expired_token(
    service: AuthService, repo: FakeUserRepository
) -> None:
    expired_service = AuthService(repo=repo, jwt_secret=_SECRET, jwt_expires_seconds=-1)
    expired_service.register("bob@example.com", "bob", "pass")
    token = expired_service.login("bob@example.com", "pass")

    with pytest.raises(TokenError, match="expired"):
        service.get_current_user(token)


def test_get_current_user_rejects_wrong_secret(service: AuthService) -> None:
    service.register("alice@example.com", "alice", "s3cr3t")
    other_secret = "different-secret-key-that-is-at-least-32-bytes"
    other_service = AuthService(
        repo=FakeUserRepository(), jwt_secret=other_secret, jwt_expires_seconds=_EXPIRES
    )
    other_service.register("alice@example.com", "alice", "s3cr3t")
    token = other_service.login("alice@example.com", "s3cr3t")

    with pytest.raises(TokenError):
        service.get_current_user(token)


def test_get_current_user_rejects_token_for_deleted_user(service: AuthService) -> None:
    service.register("alice@example.com", "alice", "s3cr3t")
    token = service.login("alice@example.com", "s3cr3t")

    # Simulate a user removed after token issuance.
    service._repo._store.clear()  # type: ignore[attr-defined]

    with pytest.raises(AuthError, match="User not found"):
        service.get_current_user(token)


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


def test_logout_is_a_noop(service: AuthService) -> None:
    service.register("alice@example.com", "alice", "s3cr3t")
    token = service.login("alice@example.com", "s3cr3t")

    # Should not raise
    service.logout(token)


# ---------------------------------------------------------------------------
# domain helpers – password and JWT
# ---------------------------------------------------------------------------


def test_verify_password_correct() -> None:
    from backend.domain.auth import verify_password

    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed) is True


def test_verify_password_wrong() -> None:
    from backend.domain.auth import verify_password

    hashed = hash_password("hunter2")
    assert verify_password("wrong", hashed) is False


_TOKEN_SECRET = "token-test-secret-key-at-least-32-bytes-long"


def test_issue_and_verify_token_roundtrip() -> None:
    from backend.domain.auth import issue_token, verify_token

    user_id = uuid4()
    token = issue_token(user_id=user_id, secret=_TOKEN_SECRET, expires_seconds=60)
    decoded_id = verify_token(token, _TOKEN_SECRET)

    assert decoded_id == user_id


def test_verify_token_rejects_tampered_token() -> None:
    from backend.domain.auth import issue_token, verify_token

    token = issue_token(user_id=uuid4(), secret=_TOKEN_SECRET, expires_seconds=60)
    tampered = token[:-4] + "XXXX"

    with pytest.raises(TokenError):
        verify_token(tampered, _TOKEN_SECRET)
