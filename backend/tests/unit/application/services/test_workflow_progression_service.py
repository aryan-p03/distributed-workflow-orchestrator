from __future__ import annotations

from sqlalchemy.orm import Session

from backend.application.services.workflow_progression_service import WorkflowProgressionService
from backend.domain.workflow_state import TaskState, WorkflowState
from tests.factories import create_task, create_user, create_workflow


def test_progression_moves_queued_workflow_to_running(db_session: Session) -> None:
    service = WorkflowProgressionService()
    user = create_user(db_session, email="running-wf@example.com", username="running-wf")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.QUEUED)
    create_task(
        db_session,
        workflow_id=workflow.id,
        sequence=1,
        task_type="delay",
        state=TaskState.RUNNING,
    )
    db_session.refresh(workflow, attribute_names=["tasks"])

    state = service.apply_progression(workflow=workflow)

    assert state == WorkflowState.RUNNING
    assert workflow.state == WorkflowState.RUNNING


def test_progression_marks_workflow_success_when_all_tasks_succeed(db_session: Session) -> None:
    service = WorkflowProgressionService()
    user = create_user(db_session, email="success-wf@example.com", username="success-wf")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.RUNNING)
    create_task(
        db_session,
        workflow_id=workflow.id,
        sequence=1,
        task_type="delay",
        state=TaskState.SUCCESS,
    )
    create_task(
        db_session,
        workflow_id=workflow.id,
        sequence=2,
        task_type="url_check",
        state=TaskState.SUCCESS,
    )
    db_session.refresh(workflow, attribute_names=["tasks"])

    state = service.apply_progression(workflow=workflow)

    assert state == WorkflowState.SUCCESS
    assert workflow.state == WorkflowState.SUCCESS


def test_progression_marks_workflow_failed_when_any_task_fails(db_session: Session) -> None:
    service = WorkflowProgressionService()
    user = create_user(db_session, email="failed-wf@example.com", username="failed-wf")
    workflow = create_workflow(db_session, user_id=user.id, state=WorkflowState.RUNNING)
    create_task(
        db_session,
        workflow_id=workflow.id,
        sequence=1,
        task_type="delay",
        state=TaskState.SUCCESS,
    )
    create_task(
        db_session,
        workflow_id=workflow.id,
        sequence=2,
        task_type="url_check",
        state=TaskState.FAILED,
    )
    db_session.refresh(workflow, attribute_names=["tasks"])

    state = service.apply_progression(workflow=workflow)

    assert state == WorkflowState.FAILED
    assert workflow.state == WorkflowState.FAILED
