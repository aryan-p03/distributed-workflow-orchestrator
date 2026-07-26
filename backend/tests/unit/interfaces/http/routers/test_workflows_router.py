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
    WorkflowTaskNotFoundError,
)
from backend.application.workflow_templates import WorkflowTemplateError
from backend.domain.auth import AuthUser
from backend.domain.workflow_state import TaskState, WorkflowState
from backend.interfaces.http.routers.workflows import create_workflow_router
from tests.conftest import AuthenticatedClient
from tests.factories import create_task, create_task_log, create_workflow

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


def _workflow_record(
    *,
    workflow_id: int = 7,
    user_id: Any = _OWNER_ID,
    workflow_state: WorkflowState = WorkflowState.QUEUED,
    task_state: TaskState = TaskState.QUEUED,
) -> Any:
    return SimpleNamespace(
        id=workflow_id,
        user_id=user_id,
        name="Process Q1",
        state=workflow_state,
        created_at=_FIXED_NOW,
        updated_at=_FIXED_NOW,
        tasks=[
            SimpleNamespace(
                id=1,
                workflow_id=workflow_id,
                sequence=1,
                name="Fetch",
                task_type="document.fetch",
                state=task_state,
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
    workflow_svc.create_workflow.return_value = _workflow_record(
        user_id=_OWNER_ID,
        workflow_state=WorkflowState.CREATED,
        task_state=TaskState.CREATED,
    )

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
    assert body["state"] == "created"
    assert body["tasks"][0]["state"] == "created"
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


def test_workflow_read_endpoints_require_authentication() -> None:
    workflow_svc = MagicMock()

    with TestClient(_app_with_services(current_user=None, workflow_service=workflow_svc)) as client:
        list_resp = client.get("/workflows")
        detail_resp = client.get("/workflows/1")
        task_resp = client.get("/workflows/1/tasks/1")
        logs_resp = client.get("/workflows/1/tasks/1/logs")

    assert list_resp.status_code == 401
    assert detail_resp.status_code == 401
    assert task_resp.status_code == 401
    assert logs_resp.status_code == 401


def test_list_workflows_returns_paged_items() -> None:
    workflow_svc = MagicMock()
    workflow_svc.list_workflows.return_value = [
        _workflow_record(workflow_id=21, user_id=_OWNER_ID),
        _workflow_record(workflow_id=22, user_id=_OWNER_ID),
    ]
    workflow_svc.count_workflows.return_value = 2

    with TestClient(
        _app_with_services(current_user=_OWNER, workflow_service=workflow_svc)
    ) as client:
        resp = client.get(
            "/workflows?limit=2&offset=0",
            headers={"Authorization": "Bearer valid.token"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["total"] == 2
    assert [item["id"] for item in body["items"]] == [21, 22]
    workflow_svc.list_workflows.assert_called_once_with(user_id=_OWNER_ID, limit=2, offset=0)
    workflow_svc.count_workflows.assert_called_once_with(user_id=_OWNER_ID)


def test_get_workflow_detail_returns_200() -> None:
    workflow_svc = MagicMock()
    workflow_svc.get_workflow.return_value = _workflow_record(workflow_id=77, user_id=_OWNER_ID)

    with TestClient(
        _app_with_services(current_user=_OWNER, workflow_service=workflow_svc)
    ) as client:
        resp = client.get(
            "/workflows/77",
            headers={"Authorization": "Bearer valid.token"},
        )

    assert resp.status_code == 200
    assert resp.json()["id"] == 77
    workflow_svc.get_workflow.assert_called_once_with(user_id=_OWNER_ID, workflow_id=77)


def test_get_workflow_task_returns_200() -> None:
    workflow_svc = MagicMock()
    workflow_svc.get_task.return_value = _workflow_record().tasks[0]

    with TestClient(
        _app_with_services(current_user=_OWNER, workflow_service=workflow_svc)
    ) as client:
        resp = client.get(
            "/workflows/7/tasks/1",
            headers={"Authorization": "Bearer valid.token"},
        )

    assert resp.status_code == 200
    assert resp.json()["id"] == 1
    workflow_svc.get_task.assert_called_once_with(user_id=_OWNER_ID, workflow_id=7, task_id=1)


def test_get_workflow_task_logs_returns_200() -> None:
    workflow_svc = MagicMock()
    workflow_svc.list_task_logs.return_value = [
        SimpleNamespace(
            id=10,
            task_id=1,
            message="queued",
            level="INFO",
            created_at=_FIXED_NOW,
        )
    ]
    workflow_svc.count_task_logs.return_value = 1

    with TestClient(
        _app_with_services(current_user=_OWNER, workflow_service=workflow_svc)
    ) as client:
        resp = client.get(
            "/workflows/7/tasks/1/logs",
            headers={"Authorization": "Bearer valid.token"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert body["total"] == 1
    assert body["items"][0]["message"] == "queued"
    workflow_svc.list_task_logs.assert_called_once_with(
        user_id=_OWNER_ID,
        workflow_id=7,
        task_id=1,
        limit=50,
        offset=0,
    )
    workflow_svc.count_task_logs.assert_called_once_with(
        user_id=_OWNER_ID,
        workflow_id=7,
        task_id=1,
    )


def test_workflow_read_endpoints_map_ownership_and_not_found_errors() -> None:
    workflow_svc = MagicMock()
    workflow_svc.get_workflow.side_effect = WorkflowAuthorizationError(
        "Cannot access another user's workflow"
    )
    workflow_svc.get_task.side_effect = WorkflowTaskNotFoundError("Task not found")
    workflow_svc.list_task_logs.side_effect = WorkflowNotFoundError("Workflow not found")

    with TestClient(
        _app_with_services(current_user=_OWNER, workflow_service=workflow_svc)
    ) as client:
        workflow_resp = client.get(
            "/workflows/77",
            headers={"Authorization": "Bearer valid.token"},
        )
        task_resp = client.get(
            "/workflows/77/tasks/2",
            headers={"Authorization": "Bearer valid.token"},
        )
        logs_resp = client.get(
            "/workflows/77/tasks/2/logs",
            headers={"Authorization": "Bearer valid.token"},
        )

    assert workflow_resp.status_code == 403
    assert task_resp.status_code == 404
    assert logs_resp.status_code == 404


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
    assert create_resp.json()["state"] == "created"
    assert [task["state"] for task in create_resp.json()["tasks"]] == [
        "created",
        "created",
        "created",
    ]
    workflow_id = create_resp.json()["id"]

    run_resp = authenticated_client.client.post(
        f"/workflows/{workflow_id}/run",
        headers=authenticated_client.auth_headers,
    )
    assert run_resp.status_code == 202
    assert run_resp.json()["state"] == "queued"


def test_workflow_run_publishes_first_task_once_in_real_stack(
    authenticated_client: AuthenticatedClient,
    monkeypatch: Any,
) -> None:
    dispatched_task_ids: list[int] = []

    def _capture_enqueue(*, task_id: int, payload: dict[str, object] | None = None) -> str:
        dispatched_task_ids.append(task_id)
        return f"queued-{task_id}"

    monkeypatch.setattr(
        "backend.infrastructure.task_queue_dispatcher.enqueue_task_execution",
        _capture_enqueue,
    )

    create_resp = authenticated_client.client.post(
        "/workflows",
        headers=authenticated_client.auth_headers,
        json={
            "template_name": "release_pipeline",
            "payload": {
                "service_name": "api",
                "release_version": "2026.07.26",
                "environment": "staging",
            },
        },
    )
    assert create_resp.status_code == 201
    workflow_id = create_resp.json()["id"]
    first_task_id = create_resp.json()["tasks"][0]["id"]

    first_run_resp = authenticated_client.client.post(
        f"/workflows/{workflow_id}/run",
        headers=authenticated_client.auth_headers,
    )
    second_run_resp = authenticated_client.client.post(
        f"/workflows/{workflow_id}/run",
        headers=authenticated_client.auth_headers,
    )

    assert first_run_resp.status_code == 202
    assert second_run_resp.status_code == 409
    assert dispatched_task_ids == [first_task_id]


def test_workflow_create_initializes_empty_logs_in_real_stack(
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
    body = create_resp.json()
    task_id = body["tasks"][0]["id"]

    logs_resp = authenticated_client.client.get(
        f"/workflows/{body['id']}/tasks/{task_id}/logs",
        headers=authenticated_client.auth_headers,
    )

    assert body["name"] == "Deploy api 2026.07.18"
    assert body["tasks"][0]["retry_count"] == 0
    assert body["tasks"][0]["result"] is None
    assert logs_resp.status_code == 200
    assert logs_resp.json()["items"] == []
    assert logs_resp.json()["total"] == 0


def test_create_workflow_returns_422_for_invalid_template_in_real_stack(
    authenticated_client: AuthenticatedClient,
) -> None:
    resp = authenticated_client.client.post(
        "/workflows",
        headers=authenticated_client.auth_headers,
        json={"template_name": "invalid", "payload": {}},
    )

    assert resp.status_code == 422
    assert "Unsupported workflow template" in resp.json()["detail"]


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


def test_illegal_second_run_returns_409_in_real_stack(
    authenticated_client: AuthenticatedClient,
) -> None:
    create_resp = authenticated_client.client.post(
        "/workflows",
        headers=authenticated_client.auth_headers,
        json={
            "template_name": "document_processing",
            "payload": {
                "document_name": "Q3 Statement",
                "source_uri": "s3://incoming/q3.pdf",
                "destination_uri": "s3://processed/q3.json",
            },
        },
    )
    assert create_resp.status_code == 201
    workflow_id = create_resp.json()["id"]

    first_run_resp = authenticated_client.client.post(
        f"/workflows/{workflow_id}/run",
        headers=authenticated_client.auth_headers,
    )
    second_run_resp = authenticated_client.client.post(
        f"/workflows/{workflow_id}/run",
        headers=authenticated_client.auth_headers,
    )

    assert first_run_resp.status_code == 202
    assert second_run_resp.status_code == 409
    assert "cannot be queued" in second_run_resp.json()["detail"]


def test_workflow_read_endpoints_in_real_stack(
    authenticated_client: AuthenticatedClient,
    db_session: Any,
) -> None:
    create_resp = authenticated_client.client.post(
        "/workflows",
        headers=authenticated_client.auth_headers,
        json={
            "template_name": "document_processing",
            "payload": {
                "document_name": "Q2 Statement",
                "source_uri": "s3://incoming/q2.pdf",
                "destination_uri": "s3://processed/q2.json",
            },
        },
    )
    assert create_resp.status_code == 201
    workflow_id = create_resp.json()["id"]
    task_id = create_resp.json()["tasks"][0]["id"]

    workflow = create_workflow(
        db_session,
        user_id=authenticated_client.user.id,
        name="Log workflow",
    )
    task = create_task(db_session, workflow_id=workflow.id, sequence=1)
    create_task_log(db_session, task_id=task.id, message="task queued")
    db_session.commit()

    list_resp = authenticated_client.client.get(
        "/workflows",
        headers=authenticated_client.auth_headers,
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 2

    detail_resp = authenticated_client.client.get(
        f"/workflows/{workflow_id}",
        headers=authenticated_client.auth_headers,
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == workflow_id

    task_resp = authenticated_client.client.get(
        f"/workflows/{workflow_id}/tasks/{task_id}",
        headers=authenticated_client.auth_headers,
    )
    assert task_resp.status_code == 200
    assert task_resp.json()["id"] == task_id

    logs_resp = authenticated_client.client.get(
        f"/workflows/{workflow.id}/tasks/{task.id}/logs",
        headers=authenticated_client.auth_headers,
    )
    assert logs_resp.status_code == 200
    assert logs_resp.json()["items"][0]["message"] == "task queued"


def test_non_owner_cannot_read_workflow_in_real_stack(
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
            "email": "viewer@example.com",
            "username": "viewer",
            "password": "secret123",
        },
    )
    assert register_resp.status_code == 201

    login_resp = authenticated_client.client.post(
        "/auth/login",
        json={"email": "viewer@example.com", "password": "secret123"},
    )
    assert login_resp.status_code == 200
    viewer_token = login_resp.json()["access_token"]

    detail_resp = authenticated_client.client.get(
        f"/workflows/{workflow_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert detail_resp.status_code == 403
