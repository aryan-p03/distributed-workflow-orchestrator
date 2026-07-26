"""Integration tests: restart and recovery behavior under dependency interruptions."""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app import create_app
from backend.domain.workflow_state import TaskState, WorkflowState
from backend.infrastructure.config import get_settings
from backend.infrastructure.db.models import Task, Workflow
from backend.worker.handlers import HandlerResult, dispatch_task_handler
from backend.worker.tasks import execute_task
from tests.factories import create_task, create_user, create_workflow


def test_worker_crash_mid_execution_rolls_back_and_is_recoverable(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If a worker crashes before commit, task state is not corrupted and can be retried."""
    user = create_user(db_session, email="restart-worker@example.com", username="restart-worker")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Wait 1 second",
        task_type="delay",
        state=TaskState.QUEUED,
        sequence=1,
    )
    db_session.commit()

    crashed = {"value": False}

    def crash_once(
        *,
        task_type: str,
        task_name: str,
        payload: Mapping[str, object] | None = None,
    ) -> HandlerResult:
        if not crashed["value"]:
            crashed["value"] = True
            raise KeyboardInterrupt("simulated worker crash")
        return dispatch_task_handler(
            task_type=task_type,
            task_name=task_name,
            payload=payload,
        )

    monkeypatch.setattr("backend.worker.tasks.dispatch_task_handler", crash_once)

    with pytest.raises(KeyboardInterrupt, match="simulated worker crash"):
        execute_task(task.id, {"seconds": 1})

    db_session.expire_all()
    persisted_task = db_session.get(Task, task.id)
    persisted_workflow = db_session.get(Workflow, workflow.id)
    assert persisted_task is not None
    assert persisted_workflow is not None
    assert persisted_task.state == TaskState.QUEUED
    assert persisted_task.retry_count == 0
    assert persisted_task.result is None
    assert persisted_workflow.state == WorkflowState.QUEUED

    result = execute_task(task.id, {"seconds": 1})
    assert result["status"] == "success"

    db_session.expire_all()
    final_task = db_session.get(Task, task.id)
    final_workflow = db_session.get(Workflow, workflow.id)
    assert final_task is not None
    assert final_workflow is not None
    assert final_task.state == TaskState.SUCCESS
    assert final_workflow.state == WorkflowState.SUCCESS


def test_api_restart_preserves_active_workflow_and_allows_completion(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API process restart must preserve persisted workflow/task state for active workloads."""
    user = create_user(db_session, email="restart-api@example.com", username="restart-api")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.RUNNING)
    completed_task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Wait 1 second",
        task_type="delay",
        state=TaskState.SUCCESS,
        sequence=1,
    )
    queued_task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Check https://example.com",
        task_type="url_check",
        state=TaskState.QUEUED,
        sequence=2,
    )
    db_session.commit()

    monkeypatch.setattr("backend.app.check_database_connection", lambda _url: None)
    monkeypatch.setattr("backend.app.check_redis_connection", lambda _url: None)
    monkeypatch.setattr("backend.app.sync_database_schema", lambda _url: None)

    with TestClient(create_app()) as first_client:
        assert first_client.get("/openapi.json").status_code == 200

    with TestClient(create_app()) as second_client:
        assert second_client.get("/openapi.json").status_code == 200

    db_session.expire_all()
    mid_workflow = db_session.get(Workflow, workflow.id)
    mid_completed = db_session.get(Task, completed_task.id)
    mid_queued = db_session.get(Task, queued_task.id)
    assert mid_workflow is not None
    assert mid_completed is not None
    assert mid_queued is not None
    assert mid_workflow.state == WorkflowState.RUNNING
    assert mid_completed.state == TaskState.SUCCESS
    assert mid_queued.state == TaskState.QUEUED

    result = execute_task(queued_task.id, {"url": "https://example.com"})
    assert result["status"] == "success"

    db_session.expire_all()
    final_workflow = db_session.get(Workflow, workflow.id)
    final_completed = db_session.get(Task, completed_task.id)
    final_queued = db_session.get(Task, queued_task.id)
    assert final_workflow is not None
    assert final_completed is not None
    assert final_queued is not None
    assert final_workflow.state == WorkflowState.SUCCESS
    assert final_completed.state == TaskState.SUCCESS
    assert final_queued.state == TaskState.SUCCESS


def test_api_startup_recovers_after_redis_connectivity_restored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup should fail while Redis is unavailable and pass after connectivity returns."""
    monkeypatch.setattr("backend.app.check_database_connection", lambda _url: None)
    monkeypatch.setattr("backend.app.sync_database_schema", lambda _url: None)

    redis_available = {"value": False}

    def check_redis(_url: str) -> None:
        if not redis_available["value"]:
            raise RuntimeError("redis down")

    monkeypatch.setattr("backend.app.check_redis_connection", check_redis)

    with pytest.raises(RuntimeError, match="redis down"):
        with TestClient(create_app()):
            pass

    redis_available["value"] = True

    with TestClient(create_app()) as client:
        assert client.get("/openapi.json").status_code == 200


def test_startup_dependency_order_db_then_schema_then_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Readiness checks run in deterministic dependency order during startup."""
    monkeypatch.setenv("SCHEMA_SYNC_ON_STARTUP", "true")
    get_settings.cache_clear()

    call_order: list[str] = []

    def check_db(_url: str) -> None:
        call_order.append("db")

    def sync_schema(_url: str) -> None:
        call_order.append("schema")

    def check_redis(_url: str) -> None:
        call_order.append("redis")

    monkeypatch.setattr("backend.app.check_database_connection", check_db)
    monkeypatch.setattr("backend.app.sync_database_schema", sync_schema)
    monkeypatch.setattr("backend.app.check_redis_connection", check_redis)

    try:
        with TestClient(create_app()):
            pass
    finally:
        get_settings.cache_clear()

    assert call_order == ["db", "schema", "redis"]
