"""Unit tests for the auth HTTP router.

Uses a fake AuthService to isolate transport concerns from application logic.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.domain.auth import AuthError, AuthUser, TokenError
from backend.interfaces.http.routers.auth import create_auth_router

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXED_NOW = datetime(2026, 1, 1, tzinfo=UTC)

_ALICE = AuthUser(
    id=1,
    email="alice@example.com",
    username="alice",
    password_hash="hashed",
    created_at=_FIXED_NOW,
)


def _find_dep_by_name(routes: list[Any], name: str) -> Any:
    """Return the first dependency callable whose function name is *name*."""
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        for dep in route.dependant.dependencies:
            call = dep.call
            if getattr(call, "__name__", None) == name:
                return call
    return None


def _app_with_service(service: Any) -> FastAPI:
    """Return a FastAPI app whose auth router always uses *service*."""
    app = FastAPI()

    router = create_auth_router(
        session_factory=MagicMock(),
        jwt_secret="test-secret",
        jwt_expires_seconds=3600,
    )

    # Capture the get_auth_service closure from the router's routes *before*
    # include_router, so we have the exact function object to override.
    get_svc_dep = _find_dep_by_name(router.routes, "get_auth_service")

    app.include_router(router)

    if get_svc_dep is not None:
        app.dependency_overrides[get_svc_dep] = lambda: service

    return app


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


def test_register_returns_201_with_user_payload() -> None:
    svc = MagicMock()
    svc.register.return_value = _ALICE

    with TestClient(_app_with_service(svc)) as client:
        resp = client.post(
            "/auth/register",
            json={"email": "alice@example.com", "username": "alice", "password": "secret123"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"
    assert "password_hash" not in body


def test_register_returns_409_on_duplicate() -> None:
    svc = MagicMock()
    svc.register.side_effect = AuthError("Email is already registered")

    with TestClient(_app_with_service(svc)) as client:
        resp = client.post(
            "/auth/register",
            json={"email": "alice@example.com", "username": "alice", "password": "secret123"},
        )

    assert resp.status_code == 409
    assert "Email is already registered" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_returns_bearer_token() -> None:
    svc = MagicMock()
    svc.login.return_value = "signed.jwt.token"

    with TestClient(_app_with_service(svc)) as client:
        resp = client.post(
            "/auth/login",
            json={"email": "alice@example.com", "password": "secret123"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] == "signed.jwt.token"
    assert body["token_type"] == "bearer"


def test_login_returns_401_for_bad_credentials() -> None:
    svc = MagicMock()
    svc.login.side_effect = AuthError("Invalid email or password")

    with TestClient(_app_with_service(svc)) as client:
        resp = client.post(
            "/auth/login",
            json={"email": "alice@example.com", "password": "wrong"},
        )

    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


# ---------------------------------------------------------------------------
# Me (protected)
# ---------------------------------------------------------------------------


def test_me_returns_current_user_when_authenticated() -> None:
    svc = MagicMock()
    svc.get_current_user.return_value = _ALICE

    with TestClient(_app_with_service(svc)) as client:
        resp = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer valid.token"},
        )

    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"
    svc.get_current_user.assert_called_once_with("valid.token")


def test_me_returns_401_without_token() -> None:
    svc = MagicMock()

    with TestClient(_app_with_service(svc)) as client:
        resp = client.get("/auth/me")

    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_me_returns_401_for_invalid_token() -> None:
    svc = MagicMock()
    svc.get_current_user.side_effect = TokenError("Token has expired")

    with TestClient(_app_with_service(svc)) as client:
        resp = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer expired.token"},
        )

    assert resp.status_code == 401
    assert "Token has expired" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


def test_logout_returns_204_with_valid_token() -> None:
    svc = MagicMock()

    with TestClient(_app_with_service(svc)) as client:
        resp = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer valid.token"},
        )

    assert resp.status_code == 204
    svc.logout.assert_called_once_with("valid.token")


def test_logout_returns_401_without_token() -> None:
    svc = MagicMock()

    with TestClient(_app_with_service(svc)) as client:
        resp = client.post("/auth/logout")

    assert resp.status_code == 401
