"""Integration tests: retry policy, exhaustion, and duplicate-delivery idempotency."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.workflow_state import TaskState, WorkflowState
from backend.infrastructure.db.models import Task, TaskLog, Workflow
from backend.worker.tasks import execute_task
from tests.factories import create_task, create_user, create_workflow


def test_task_fail_then_retry_then_success(db_session: Session) -> None:
    """Task fails on first attempt, returns to QUEUED, then succeeds on retry.

    Workflow stays RUNNING during retry and reaches SUCCESS after the task succeeds.
    """
    user = create_user(db_session, email="retry-ok@example.com", username="retry-ok")
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

    # First execution: handler raises → task goes back to QUEUED with retry_count=1.
    result1 = execute_task(task.id, payload={})

    assert result1["status"] == "failed"
    assert result1["data"]["retry_scheduled"] is True
    assert result1["data"]["attempt"] == 1

    db_session.expire_all()
    mid_task = db_session.get(Task, task.id)
    assert mid_task is not None
    assert mid_task.state == TaskState.QUEUED
    assert mid_task.retry_count == 1

    mid_workflow = db_session.get(Workflow, workflow.id)
    assert mid_workflow is not None
    assert mid_workflow.state == WorkflowState.RUNNING

    # Simulate transient error clearing: update task_type to a valid handler.
    mid_task.task_type = "delay"
    mid_task.name = "Wait 1 second"
    db_session.commit()

    # Second execution: task succeeds → workflow reaches SUCCESS.
    result2 = execute_task(task.id, payload={"seconds": 1})

    assert result2["status"] == "success"

    db_session.expire_all()
    final_task = db_session.get(Task, task.id)
    assert final_task is not None
    assert final_task.state == TaskState.SUCCESS
    assert final_task.retry_count == 1  # retry_count records prior failures

    final_workflow = db_session.get(Workflow, workflow.id)
    assert final_workflow is not None
    assert final_workflow.state == WorkflowState.SUCCESS


def test_retry_exhaustion_terminates_workflow(db_session: Session) -> None:
    """Task exhausts all retry attempts; workflow transitions to terminal FAILED state."""
    user = create_user(db_session, email="retry-exhaust@example.com", username="retry-exhaust")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    task = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Unsupported task",
        task_type="unsupported",
        state=TaskState.QUEUED,
        sequence=1,
        retry_count=0,
    )
    db_session.commit()

    # Attempt 1 of 3: retry scheduled.
    result1 = execute_task(task.id, payload={})
    assert result1["data"]["retry_scheduled"] is True
    assert result1["data"]["attempt"] == 1

    db_session.expire_all()
    assert db_session.get(Task, task.id).state == TaskState.QUEUED  # type: ignore[union-attr]
    assert db_session.get(Task, task.id).retry_count == 1  # type: ignore[union-attr]

    # Attempt 2 of 3: retry scheduled.
    result2 = execute_task(task.id, payload={})
    assert result2["data"]["retry_scheduled"] is True
    assert result2["data"]["attempt"] == 2

    db_session.expire_all()
    assert db_session.get(Task, task.id).state == TaskState.QUEUED  # type: ignore[union-attr]
    assert db_session.get(Task, task.id).retry_count == 2  # type: ignore[union-attr]

    # Attempt 3 of 3: budget exhausted, terminal FAILED.
    result3 = execute_task(task.id, payload={})
    assert result3["status"] == "failed"
    assert result3["data"]["retry_scheduled"] is False
    assert result3["data"]["attempt"] == 3

    db_session.expire_all()
    final_task = db_session.get(Task, task.id)
    assert final_task is not None
    assert final_task.state == TaskState.FAILED
    assert final_task.retry_count == 2  # count of retries consumed before terminal

    final_workflow = db_session.get(Workflow, workflow.id)
    assert final_workflow is not None
    assert final_workflow.state == WorkflowState.FAILED

    # Verify WARNING logs were emitted for the first two attempts.
    logs = list(
        db_session.execute(
            select(TaskLog)
            .where(TaskLog.task_id == task.id, TaskLog.level == "WARNING")
            .order_by(TaskLog.id.asc())
        )
        .scalars()
        .all()
    )
    assert len(logs) == 2


def test_duplicate_delivery_does_not_corrupt_terminal_state(db_session: Session) -> None:
    """Calling execute_task on an already-SUCCESS task raises without modifying state.

    Idempotency guarantee: duplicate delivery of a completed task cannot cause a
    second terminal progression on either the task or the workflow.
    """
    user = create_user(db_session, email="idempotent@example.com", username="idempotent")
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

    # First delivery: normal success path.
    result = execute_task(task.id, {"seconds": 1})
    assert result["status"] == "success"

    db_session.expire_all()
    assert db_session.get(Task, task.id).state == TaskState.SUCCESS  # type: ignore[union-attr]
    assert db_session.get(Workflow, workflow.id).state == WorkflowState.SUCCESS  # type: ignore[union-attr]

    # Second delivery: must raise (cannot transition SUCCESS → RUNNING) without
    # committing any state change.
    with pytest.raises(ValueError, match="cannot transition"):
        execute_task(task.id, {"seconds": 1})

    # State is unchanged after the duplicate delivery.
    db_session.expire_all()
    final_task = db_session.get(Task, task.id)
    assert final_task is not None
    assert final_task.state == TaskState.SUCCESS

    final_workflow = db_session.get(Workflow, workflow.id)
    assert final_workflow is not None
    assert final_workflow.state == WorkflowState.SUCCESS
