from __future__ import annotations

import json
from collections.abc import Mapping

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.workflow_state import TaskState, WorkflowState
from backend.infrastructure.db.models import Task, TaskLog, Workflow
from backend.worker.tasks import execute_task
from tests.factories import create_task, create_user, create_workflow


class _DispatchRecorder:
    def __init__(self) -> None:
        self.calls: list[dict[str, object | None]] = []

    def __call__(
        self,
        *,
        task_id: int,
        payload: Mapping[str, object] | None = None,
        countdown_seconds: int | None = None,
    ) -> str:
        self.calls.append(
            {
                "task_id": task_id,
                "payload": payload,
                "countdown_seconds": countdown_seconds,
            }
        )
        return f"queued-{task_id}"


@pytest.mark.parametrize(
    ("task_type", "task_name", "payload"),
    [
        ("delay", "Wait 3 seconds", {"seconds": 3}),
        ("url_check", "Check https://example.com", {"url": "https://example.com"}),
        ("csv_process", "name,score\nalpha,10\nbeta,20", {"csv_text": "name,score\nalpha,10"}),
        ("text_analyze", "Analyze this text", {"text": "Hello world. Testing now!"}),
    ],
)
def test_execute_task_dispatches_supported_handlers(
    db_session: Session,
    task_type: str,
    task_name: str,
    payload: dict[str, object],
) -> None:
    user = create_user(db_session)
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        name=task_name,
        task_type=task_type,
        state=TaskState.QUEUED,
    )
    db_session.commit()

    result = execute_task(task.id, payload)

    assert result["status"] == "success"

    db_session.expire_all()
    persisted_task = db_session.get(Task, task.id)
    assert persisted_task is not None
    assert persisted_task.state == TaskState.SUCCESS
    assert persisted_task.result is not None
    assert json.loads(persisted_task.result)["status"] == "success"

    persisted_workflow = db_session.get(Workflow, workflow.id)
    assert persisted_workflow is not None
    assert persisted_workflow.state == WorkflowState.SUCCESS

    logs = list(
        db_session.execute(
            select(TaskLog).where(TaskLog.task_id == task.id).order_by(TaskLog.id.asc())
        )
        .scalars()
        .all()
    )
    assert len(logs) == 2
    assert logs[0].message == "Task execution started"
    assert logs[0].level == "INFO"
    assert logs[1].level == "INFO"


def test_execute_task_schedules_retry_for_unknown_task_type(db_session: Session) -> None:
    user = create_user(db_session, email="unknown-type@example.com", username="unknown-type")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Unsupported task",
        task_type="unsupported",
        state=TaskState.QUEUED,
    )
    db_session.commit()

    result = execute_task(task.id, payload={})

    assert result["status"] == "failed"
    assert "Unsupported task type" in result["message"]
    assert result["data"]["retry_scheduled"] is True
    assert result["data"]["next_backoff_seconds"] == 5

    db_session.expire_all()
    persisted_task = db_session.get(Task, task.id)
    assert persisted_task is not None
    assert persisted_task.state == TaskState.QUEUED
    assert persisted_task.retry_count == 1

    persisted_workflow = db_session.get(Workflow, workflow.id)
    assert persisted_workflow is not None
    assert persisted_workflow.state == WorkflowState.RUNNING

    logs = list(
        db_session.execute(
            select(TaskLog).where(TaskLog.task_id == task.id).order_by(TaskLog.id.asc())
        )
        .scalars()
        .all()
    )
    assert len(logs) == 2
    assert logs[1].level == "WARNING"


def test_execute_task_marks_failed_when_retry_budget_exhausted(db_session: Session) -> None:
    user = create_user(db_session, email="retry-exhausted@example.com", username="retry-exhausted")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Unsupported task",
        task_type="unsupported",
        state=TaskState.QUEUED,
        retry_count=2,
    )
    db_session.commit()

    result = execute_task(task.id, payload={})

    assert result["status"] == "failed"
    assert result["data"]["retry_scheduled"] is False

    db_session.expire_all()
    persisted_task = db_session.get(Task, task.id)
    assert persisted_task is not None
    assert persisted_task.state == TaskState.FAILED
    assert persisted_task.retry_count == 2

    persisted_workflow = db_session.get(Workflow, workflow.id)
    assert persisted_workflow is not None
    assert persisted_workflow.state == WorkflowState.FAILED


def test_execute_task_rejects_invalid_transition_state(db_session: Session) -> None:
    user = create_user(
        db_session,
        email="bad-transition@example.com",
        username="bad-transition",
    )
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Wait 1 second",
        task_type="delay",
        state=TaskState.CREATED,
    )
    db_session.commit()

    with pytest.raises(ValueError, match="cannot transition"):
        execute_task(task.id, payload={"seconds": 1})


def test_execute_task_dispatches_next_queued_task_after_success(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _DispatchRecorder()
    monkeypatch.setattr("backend.worker.tasks.enqueue_task_execution", recorder)

    user = create_user(db_session, email="chain-success@example.com", username="chain-success")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    first_task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Wait 1 second",
        task_type="delay",
        state=TaskState.QUEUED,
        sequence=1,
    )
    second_task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Check https://example.com",
        task_type="url_check",
        state=TaskState.QUEUED,
        sequence=2,
    )
    db_session.commit()

    result = execute_task(first_task.id, payload={"seconds": 1})
    assert result["status"] == "success"

    assert recorder.calls == [
        {
            "task_id": second_task.id,
            "payload": None,
            "countdown_seconds": None,
        }
    ]


def test_execute_task_schedules_retry_with_backoff_countdown(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _DispatchRecorder()
    monkeypatch.setattr("backend.worker.tasks.enqueue_task_execution", recorder)

    user = create_user(db_session, email="retry-dispatch@example.com", username="retry-dispatch")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Unsupported task",
        task_type="unsupported",
        state=TaskState.QUEUED,
        sequence=1,
    )
    db_session.commit()

    result = execute_task(task.id, payload={})
    assert result["status"] == "failed"
    assert result["data"]["retry_scheduled"] is True
    assert result["data"]["next_backoff_seconds"] == 5

    assert recorder.calls == [
        {
            "task_id": task.id,
            "payload": None,
            "countdown_seconds": 5,
        }
    ]


def test_execute_task_does_not_dispatch_after_terminal_failure(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _DispatchRecorder()
    monkeypatch.setattr("backend.worker.tasks.enqueue_task_execution", recorder)

    user = create_user(db_session, email="terminal-stop@example.com", username="terminal-stop")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Unsupported task",
        task_type="unsupported",
        state=TaskState.QUEUED,
        sequence=1,
        retry_count=2,
    )
    db_session.commit()

    result = execute_task(task.id, payload={})
    assert result["status"] == "failed"
    assert result["data"]["retry_scheduled"] is False

    assert recorder.calls == []
