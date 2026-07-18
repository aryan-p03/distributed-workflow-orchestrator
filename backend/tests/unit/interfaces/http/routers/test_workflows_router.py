from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.application.services.workflow_service import (
    WorkflowAuthorizationError,
    WorkflowNotFoundError,
)
from backend.application.workflow_templates import WorkflowTemplateError
from backend.domain.auth import AuthUser
from backend.domain.workflow_state import TaskState, WorkflowState
from backend.interfaces.http.routers.workflows import create_workflow_router
from tests.conftest import AuthenticatedClient

_FIXED_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_OWNER_ID = uuid4()
_OWNER = AuthUser(
    id=_OWNER_ID,
    email="owner@example.com",
    username="owner",
    password_hash="hashed",
    created_at=_FIXED_NOW,
)


def _find_dep_by_name(routes: list[Any], name: str) -> Any:
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        for dep in route.dependant.dependencies:
            call = dep.call
            if getattr(call, "__name__", None) == name:
                return call
    return None


def _workflow_record(*, workflow_id: int = 7, user_id: Any = _OWNER_ID) -> Any:
    return SimpleNamespace(
        id=workflow_id,
        user_id=user_id,
        name="Process Q1",
        state=WorkflowState.QUEUED,
        created_at=_FIXED_NOW,
        updated_at=_FIXED_NOW,
        tasks=[
            SimpleNamespace(
                id=1,
                sequence=1,
                name="Fetch",
                task_type="document.fetch",
                state=TaskState.QUEUED,
                retry_count=0,
                result=None,
                created_at=_FIXED_NOW,
                updated_at=_FIXED_NOW,
            )
        ],
    )


def _app_with_services(*, current_user: AuthUser | None, workflow_service: Any) -> FastAPI:
    app = FastAPI()

    router = create_workflow_router(
        session_factory=MagicMock(),
        jwt_secret="test-secret",
        jwt_expires_seconds=3600,
    )

    get_current_user_dep = _find_dep_by_name(router.routes, "get_current_user")
    get_workflow_svc_dep = _find_dep_by_name(router.routes, "get_workflow_service")

    app.include_router(router)

    if get_current_user_dep is not None and current_user is not None:
        app.dependency_overrides[get_current_user_dep] = lambda: current_user
    if get_workflow_svc_dep is not None:
        app.dependency_overrides[get_workflow_svc_dep] = lambda: workflow_service

    return app


def test_create_workflow_returns_201_and_delegates_to_service() -> None:
    workflow_svc = MagicMock()
    workflow_svc.create_workflow.return_value = _workflow_record(user_id=_OWNER_ID)

    with TestClient(
        _app_with_services(current_user=_OWNER, workflow_service=workflow_svc)
    ) as client:
        resp = client.post(
            "/workflows",
            headers={"Authorization": "Bearer valid.token"},
            json={
                "template_name": "document_processing",
                "payload": {
                    "document_name": "Q1 Statement",
                    "source_uri": "s3://incoming/q1.pdf",
                    "destination_uri": "s3://processed/q1.json",
                },
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 7
    assert body["state"] == "queued"
    workflow_svc.create_workflow.assert_called_once_with(
        user_id=_OWNER_ID,
        template_name="document_processing",
        payload={
            "document_name": "Q1 Statement",
            "source_uri": "s3://incoming/q1.pdf",
            "destination_uri": "s3://processed/q1.json",
        },
    )


def test_create_workflow_returns_422_for_invalid_template_payload() -> None:
    workflow_svc = MagicMock()
    workflow_svc.create_workflow.side_effect = WorkflowTemplateError(
        "Unsupported workflow template"
    )

    with TestClient(
        _app_with_services(current_user=_OWNER, workflow_service=workflow_svc)
    ) as client:
        resp = client.post(
            "/workflows",
            headers={"Authorization": "Bearer valid.token"},
            json={"template_name": "invalid", "payload": {}},
        )

    assert resp.status_code == 422
    assert "Unsupported workflow template" in resp.json()["detail"]


def test_run_workflow_returns_202_and_delegates_to_service() -> None:
    workflow_svc = MagicMock()
    workflow_svc.run_workflow.return_value = _workflow_record(workflow_id=42, user_id=_OWNER_ID)

    with TestClient(
        _app_with_services(current_user=_OWNER, workflow_service=workflow_svc)
    ) as client:
        resp = client.post(
            "/workflows/42/run",
            headers={"Authorization": "Bearer valid.token"},
        )

    assert resp.status_code == 202
    assert resp.json()["id"] == 42
    workflow_svc.run_workflow.assert_called_once_with(user_id=_OWNER_ID, workflow_id=42)


def test_run_workflow_returns_403_for_non_owner_access() -> None:
    workflow_svc = MagicMock()
    workflow_svc.run_workflow.side_effect = WorkflowAuthorizationError(
        "Cannot run another user's workflow"
    )

    with TestClient(
        _app_with_services(current_user=_OWNER, workflow_service=workflow_svc)
    ) as client:
        resp = client.post(
            "/workflows/42/run",
            headers={"Authorization": "Bearer valid.token"},
        )

    assert resp.status_code == 403
    assert "another user's workflow" in resp.json()["detail"]


def test_run_workflow_returns_404_when_missing() -> None:
    workflow_svc = MagicMock()
    workflow_svc.run_workflow.side_effect = WorkflowNotFoundError("Workflow not found")

    with TestClient(
        _app_with_services(current_user=_OWNER, workflow_service=workflow_svc)
    ) as client:
        resp = client.post(
            "/workflows/99/run",
            headers={"Authorization": "Bearer valid.token"},
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Workflow not found"


def test_workflow_write_endpoints_require_authentication() -> None:
    workflow_svc = MagicMock()

    with TestClient(_app_with_services(current_user=None, workflow_service=workflow_svc)) as client:
        create_resp = client.post(
            "/workflows",
            json={"template_name": "document_processing", "payload": {}},
        )
        run_resp = client.post("/workflows/1/run")

    assert create_resp.status_code == 401
    assert run_resp.status_code == 401


def test_workflow_create_and_run_in_real_stack(
    authenticated_client: AuthenticatedClient,
) -> None:
    create_resp = authenticated_client.client.post(
        "/workflows",
        headers=authenticated_client.auth_headers,
        json={
            "template_name": "document_processing",
            "payload": {
                "document_name": "Q1 Statement",
                "source_uri": "s3://incoming/q1.pdf",
                "destination_uri": "s3://processed/q1.json",
            },
        },
    )
    assert create_resp.status_code == 201
    workflow_id = create_resp.json()["id"]

    run_resp = authenticated_client.client.post(
        f"/workflows/{workflow_id}/run",
        headers=authenticated_client.auth_headers,
    )
    assert run_resp.status_code == 202
    assert run_resp.json()["state"] == "queued"


def test_non_owner_cannot_run_workflow_in_real_stack(
    authenticated_client: AuthenticatedClient,
) -> None:
    create_resp = authenticated_client.client.post(
        "/workflows",
        headers=authenticated_client.auth_headers,
        json={
            "template_name": "release_pipeline",
            "payload": {
                "service_name": "api",
                "release_version": "2026.07.18",
                "environment": "staging",
            },
        },
    )
    assert create_resp.status_code == 201
    workflow_id = create_resp.json()["id"]

    register_resp = authenticated_client.client.post(
        "/auth/register",
        json={
            "email": "intruder@example.com",
            "username": "intruder",
            "password": "secret123",
        },
    )
    assert register_resp.status_code == 201

    login_resp = authenticated_client.client.post(
        "/auth/login",
        json={"email": "intruder@example.com", "password": "secret123"},
    )
    assert login_resp.status_code == 200
    intruder_token = login_resp.json()["access_token"]

    run_resp = authenticated_client.client.post(
        f"/workflows/{workflow_id}/run",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert run_resp.status_code == 403
