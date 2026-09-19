"""Integration tests: successful execution paths for worker tasks and workflow progression."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from backend.domain.workflow_state import TaskState, WorkflowState
from backend.infrastructure.db.models import Task, Workflow
from backend.worker.tasks import execute_task
from tests.factories import create_task, create_user, create_workflow


class _DispatchRecorder:
    def __init__(self) -> None:
        self.calls: list[dict[str, object | None]] = []

    def __call__(
        self,
        *,
        task_id: int,
        countdown_seconds: int | None = None,
    ) -> str:
        self.calls.append(
            {
                "task_id": task_id,
                "countdown_seconds": countdown_seconds,
            }
        )
        return f"queued-{task_id}"


def test_single_task_workflow_reaches_success(db_session: Session) -> None:
    """A workflow with one QUEUED task transitions fully to SUCCESS after execution."""
    user = create_user(db_session, email="exec-single@example.com", username="exec-single")
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

    result = execute_task(task.id)

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


def test_multi_task_workflow_stays_running_until_all_tasks_complete(
    db_session: Session,
) -> None:
    """Workflow stays RUNNING after first task succeeds; only reaches SUCCESS when all tasks do."""
    user = create_user(db_session, email="exec-multi@example.com", username="exec-multi")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    task1 = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Wait 1 second",
        task_type="delay",
        state=TaskState.QUEUED,
        sequence=1,
    )
    task2 = create_task(
        db_session,
        workflow_id=workflow.id,
        name="Check https://example.com",
        task_type="url_check",
        state=TaskState.QUEUED,
        sequence=2,
    )
    db_session.commit()

    # Execute first task; workflow should be RUNNING while task2 is still QUEUED.
    result1 = execute_task(task1.id)
    assert result1["status"] == "success"

    db_session.expire_all()
    mid_workflow = db_session.get(Workflow, workflow.id)
    assert mid_workflow is not None
    assert mid_workflow.state == WorkflowState.RUNNING

    mid_task1 = db_session.get(Task, task1.id)
    mid_task2 = db_session.get(Task, task2.id)
    assert mid_task1 is not None and mid_task1.state == TaskState.SUCCESS
    assert mid_task2 is not None and mid_task2.state == TaskState.QUEUED

    # Execute second task; workflow should now be SUCCESS.
    result2 = execute_task(task2.id)
    assert result2["status"] == "success"

    db_session.expire_all()
    final_workflow = db_session.get(Workflow, workflow.id)
    assert final_workflow is not None
    assert final_workflow.state == WorkflowState.SUCCESS

    final_task1 = db_session.get(Task, task1.id)
    final_task2 = db_session.get(Task, task2.id)
    assert final_task1 is not None and final_task1.state == TaskState.SUCCESS
    assert final_task2 is not None and final_task2.state == TaskState.SUCCESS


def test_multi_task_success_auto_dispatches_follow_up_task(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful completion auto-dispatches the next queued task in sequence."""
    recorder = _DispatchRecorder()
    monkeypatch.setattr("backend.worker.tasks.enqueue_task_execution", recorder)

    user = create_user(db_session, email="exec-chain@example.com", username="exec-chain")
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

    result = execute_task(first_task.id)
    assert result["status"] == "success"

    assert recorder.calls == [
        {
            "task_id": second_task.id,
            "countdown_seconds": None,
        }
    ]
