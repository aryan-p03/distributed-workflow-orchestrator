from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.application.services.workflow_service import WorkflowService, WorkflowServiceError
from backend.application.workflow_templates import WorkflowTemplateError
from backend.domain.workflow_state import TaskState, WorkflowState
from backend.infrastructure.db.models import Task, Workflow
from tests.factories import create_task, create_task_log, create_user, create_workflow


@pytest.fixture()
def workflow_service(db_session: Session) -> WorkflowService:
    return WorkflowService(db_session)


def test_create_workflow_persists_workflow_and_ordered_tasks(
    db_session: Session,
    workflow_service: WorkflowService,
) -> None:
    user = create_user(db_session, email="owner@example.com", username="owner")

    workflow = workflow_service.create_workflow(
        user_id=user.id,
        template_name="document_processing",
        payload={
            "workflow_name": "Quarterly statement import",
            "document_name": "Q1 Statement",
            "source_uri": "s3://incoming/q1.pdf",
            "destination_uri": "s3://processed/q1.json",
        },
    )
    db_session.commit()

    persisted_workflow = db_session.execute(
        select(Workflow).where(Workflow.id == workflow.id)
    ).scalar_one()
    persisted_tasks = (
        db_session.execute(
            select(Task).where(Task.workflow_id == workflow.id).order_by(Task.sequence)
        )
        .scalars()
        .all()
    )

    assert persisted_workflow.user_id == user.id
    assert persisted_workflow.name == "Quarterly statement import"
    assert [task.sequence for task in persisted_tasks] == [1, 2, 3]
    assert [task.name for task in persisted_tasks] == [
        "Fetch Q1 Statement",
        "Transform Q1 Statement",
        "Publish to s3://processed/q1.json",
    ]
    assert [task.task_type for task in persisted_tasks] == [
        "document.fetch",
        "document.transform",
        "document.publish",
    ]


def test_create_workflow_rejects_unknown_template(
    db_session: Session,
    workflow_service: WorkflowService,
) -> None:
    user = create_user(db_session, email="owner@example.com", username="owner")

    with pytest.raises(WorkflowTemplateError, match="Unsupported workflow template"):
        workflow_service.create_workflow(
            user_id=user.id,
            template_name="unknown_template",
            payload={},
        )

    assert db_session.execute(select(Workflow)).scalars().all() == []


def test_create_workflow_rejects_invalid_payload(
    db_session: Session,
    workflow_service: WorkflowService,
) -> None:
    user = create_user(db_session, email="owner@example.com", username="owner")

    with pytest.raises(WorkflowTemplateError, match="workflow_name"):
        workflow_service.create_workflow(
            user_id=user.id,
            template_name="document_processing",
            payload={
                "workflow_name": "   ",
                "document_name": "Q1 Statement",
                "source_uri": "s3://incoming/q1.pdf",
                "destination_uri": "s3://processed/q1.json",
            },
        )


def test_create_workflow_rejects_missing_authenticated_user(
    workflow_service: WorkflowService,
) -> None:
    with pytest.raises(WorkflowServiceError, match="Authenticated user not found"):
        workflow_service.create_workflow(
            user_id=uuid4(),
            template_name="release_pipeline",
            payload={
                "service_name": "api",
                "release_version": "2026.07.17",
                "environment": "staging",
            },
        )


def test_run_workflow_queues_workflow_and_tasks(
    db_session: Session,
    workflow_service: WorkflowService,
) -> None:
    owner = create_user(db_session, email="owner@example.com", username="owner")
    workflow = create_workflow(db_session, user_id=owner.id, state=WorkflowState.CREATED)
    first_task = create_task(
        db_session,
        workflow_id=workflow.id,
        sequence=1,
        state=TaskState.CREATED,
    )
    second_task = create_task(
        db_session,
        workflow_id=workflow.id,
        sequence=2,
        state=TaskState.CREATED,
    )
    db_session.commit()

    queued_workflow = workflow_service.run_workflow(user_id=owner.id, workflow_id=workflow.id)
    db_session.commit()

    assert queued_workflow.state == WorkflowState.QUEUED

    persisted_tasks = (
        db_session.execute(
            select(Task).where(Task.workflow_id == workflow.id).order_by(Task.sequence)
        )
        .scalars()
        .all()
    )

    assert [task.id for task in persisted_tasks] == [first_task.id, second_task.id]
    assert [task.state for task in persisted_tasks] == [TaskState.QUEUED, TaskState.QUEUED]


def test_run_workflow_rejects_non_owner(
    db_session: Session,
    workflow_service: WorkflowService,
) -> None:
    owner = create_user(db_session, email="owner@example.com", username="owner")
    intruder = create_user(db_session, email="intruder@example.com", username="intruder")
    workflow = create_workflow(db_session, user_id=owner.id)
    create_task(db_session, workflow_id=workflow.id, state=TaskState.CREATED)
    db_session.commit()

    with pytest.raises(WorkflowServiceError, match="another user's workflow"):
        workflow_service.run_workflow(user_id=intruder.id, workflow_id=workflow.id)


def test_run_workflow_rejects_invalid_workflow_state(
    db_session: Session,
    workflow_service: WorkflowService,
) -> None:
    owner = create_user(db_session, email="owner@example.com", username="owner")
    workflow = create_workflow(db_session, user_id=owner.id, state=WorkflowState.RUNNING)
    create_task(db_session, workflow_id=workflow.id, state=TaskState.RUNNING)
    db_session.commit()

    with pytest.raises(WorkflowServiceError, match="cannot be queued"):
        workflow_service.run_workflow(user_id=owner.id, workflow_id=workflow.id)


def test_list_workflows_returns_only_owned_items_with_pagination(
    db_session: Session,
    workflow_service: WorkflowService,
) -> None:
    owner = create_user(db_session, email="owner@example.com", username="owner")
    other = create_user(db_session, email="other@example.com", username="other")
    own_first = create_workflow(db_session, user_id=owner.id, name="Owner A")
    own_second = create_workflow(db_session, user_id=owner.id, name="Owner B")
    create_workflow(db_session, user_id=other.id, name="Other C")
    db_session.commit()

    listed = workflow_service.list_workflows(user_id=owner.id, limit=1, offset=0)
    total = workflow_service.count_workflows(user_id=owner.id)

    assert total == 2
    assert len(listed) == 1
    assert listed[0].id in {own_first.id, own_second.id}
    assert listed[0].user_id == owner.id


def test_get_workflow_rejects_non_owner(
    db_session: Session,
    workflow_service: WorkflowService,
) -> None:
    owner = create_user(db_session, email="owner@example.com", username="owner")
    intruder = create_user(db_session, email="intruder@example.com", username="intruder")
    workflow = create_workflow(db_session, user_id=owner.id)
    db_session.commit()

    with pytest.raises(WorkflowServiceError, match="another user's workflow"):
        workflow_service.get_workflow(user_id=intruder.id, workflow_id=workflow.id)


def test_get_task_and_list_logs_return_expected_records(
    db_session: Session,
    workflow_service: WorkflowService,
) -> None:
    owner = create_user(db_session, email="owner@example.com", username="owner")
    workflow = create_workflow(db_session, user_id=owner.id)
    first_task = create_task(db_session, workflow_id=workflow.id, sequence=1, name="First")
    second_task = create_task(db_session, workflow_id=workflow.id, sequence=2, name="Second")
    create_task_log(db_session, task_id=second_task.id, message="queued")
    create_task_log(db_session, task_id=second_task.id, message="running")
    db_session.commit()

    task = workflow_service.get_task(
        user_id=owner.id,
        workflow_id=workflow.id,
        task_id=second_task.id,
    )
    logs = workflow_service.list_task_logs(
        user_id=owner.id,
        workflow_id=workflow.id,
        task_id=second_task.id,
        limit=10,
        offset=0,
    )
    total = workflow_service.count_task_logs(
        user_id=owner.id,
        workflow_id=workflow.id,
        task_id=second_task.id,
    )

    assert task.id == second_task.id
    assert task.sequence == 2
    assert first_task.id != task.id
    assert [item.message for item in logs] == ["queued", "running"]
    assert total == 2
