from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.application.services.workflow_service import WorkflowService, WorkflowServiceError
from backend.application.workflow_templates import WorkflowTemplateError
from backend.infrastructure.db.models import Task, Workflow
from tests.factories import create_user


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
