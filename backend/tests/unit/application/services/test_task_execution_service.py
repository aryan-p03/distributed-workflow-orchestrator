from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from backend.application.services.task_execution_service import TaskExecutionService
from backend.domain.workflow_state import TaskState
from tests.factories import create_task, create_user, create_workflow


def test_mark_running_rejects_terminal_state(db_session: Session) -> None:
    service = TaskExecutionService()
    user = create_user(db_session, email="terminal-task@example.com", username="terminal-task")
    workflow = create_workflow(db_session, user_id=user.id)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        task_type="delay",
        state=TaskState.SUCCESS,
    )

    with pytest.raises(ValueError, match="cannot transition"):
        service.mark_running(task=task)


def test_complete_success_persists_state_and_result(db_session: Session) -> None:
    service = TaskExecutionService()
    user = create_user(db_session, email="success-task@example.com", username="success-task")
    workflow = create_workflow(db_session, user_id=user.id)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        task_type="delay",
        state=TaskState.QUEUED,
    )

    service.mark_running(task=task)
    outcome = service.complete_success(
        task=task,
        result={"status": "success", "message": "ok", "data": {"seconds": 1}},
    )

    assert task.state == TaskState.SUCCESS
    assert task.result is not None
    assert json.loads(task.result)["status"] == "success"
    assert outcome["message"] == "ok"


def test_complete_failure_schedules_retry_with_backoff(db_session: Session) -> None:
    service = TaskExecutionService()
    user = create_user(db_session, email="retry-task@example.com", username="retry-task")
    workflow = create_workflow(db_session, user_id=user.id)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        task_type="delay",
        state=TaskState.QUEUED,
    )

    service.mark_running(task=task)
    resolution = service.complete_failure(
        task=task,
        message="boom",
        error_type="RuntimeError",
    )

    assert resolution.retry_scheduled is True
    assert resolution.backoff_seconds == 5
    assert task.state == TaskState.QUEUED
    assert task.retry_count == 1
    assert resolution.result["data"]["retry_scheduled"] is True
    assert resolution.result["data"]["next_backoff_seconds"] == 5


def test_complete_failure_exhausts_retry_budget(db_session: Session) -> None:
    service = TaskExecutionService()
    user = create_user(db_session, email="retry-exhausted@example.com", username="retry-exhausted")
    workflow = create_workflow(db_session, user_id=user.id)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        task_type="delay",
        state=TaskState.QUEUED,
        retry_count=2,
    )

    service.mark_running(task=task)
    resolution = service.complete_failure(
        task=task,
        message="still failing",
        error_type="RuntimeError",
    )

    assert resolution.retry_scheduled is False
    assert resolution.backoff_seconds is None
    assert task.state == TaskState.FAILED
    assert task.retry_count == 2
    assert resolution.result["data"]["attempt"] == 3
    assert resolution.result["data"]["retry_scheduled"] is False
