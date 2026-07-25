from __future__ import annotations

import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.workflow_state import TaskState
from backend.infrastructure.db.models import Task, TaskLog
from backend.worker.tasks import execute_task
from tests.factories import create_task, create_user, create_workflow


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
    workflow = create_workflow(db_session, user_id=user.id)
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


def test_execute_task_marks_failed_for_unknown_task_type(db_session: Session) -> None:
    user = create_user(db_session, email="unknown-type@example.com", username="unknown-type")
    workflow = create_workflow(db_session, user_id=user.id)
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

    db_session.expire_all()
    persisted_task = db_session.get(Task, task.id)
    assert persisted_task is not None
    assert persisted_task.state == TaskState.FAILED

    logs = list(
        db_session.execute(
            select(TaskLog).where(TaskLog.task_id == task.id).order_by(TaskLog.id.asc())
        )
        .scalars()
        .all()
    )
    assert len(logs) == 2
    assert logs[1].level == "ERROR"


def test_execute_task_rejects_invalid_transition_state(db_session: Session) -> None:
    user = create_user(
        db_session,
        email="bad-transition@example.com",
        username="bad-transition",
    )
    workflow = create_workflow(db_session, user_id=user.id)
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
