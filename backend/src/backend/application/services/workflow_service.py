"""Workflow creation service backed by SQLAlchemy models."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from backend.application.workflow_templates import (
    WorkflowTemplateError,
    resolve_workflow_template,
)
from backend.domain.workflow_state import (
    TaskState,
    WorkflowState,
    can_transition_task,
    can_transition_workflow,
)
from backend.infrastructure.db.models import Task, User, Workflow


class WorkflowServiceError(ValueError):
    """Raised when workflow creation cannot proceed."""


class WorkflowNotFoundError(WorkflowServiceError):
    """Raised when a workflow cannot be found."""


class WorkflowAuthorizationError(WorkflowServiceError):
    """Raised when a workflow operation is attempted by a non-owner."""


class WorkflowService:
    """Orchestrates workflow creation from predefined templates."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_workflow(
        self,
        *,
        user_id: UUID,
        template_name: str,
        payload: Mapping[str, object],
    ) -> Workflow:
        user = self._session.get(User, user_id)
        if user is None:
            raise WorkflowServiceError("Authenticated user not found")

        plan = resolve_workflow_template(template_name, payload)
        workflow = Workflow(
            user_id=user.id,
            name=plan.workflow_name,
            state=WorkflowState.CREATED,
        )
        self._session.add(workflow)
        self._session.flush()

        self._session.add_all(
            Task(
                workflow_id=workflow.id,
                sequence=task.sequence,
                name=task.name,
                task_type=task.task_type,
                state=TaskState.CREATED,
            )
            for task in plan.tasks
        )
        self._session.flush()
        self._session.refresh(workflow)
        self._session.refresh(workflow, attribute_names=["tasks"])
        return workflow

    def run_workflow(
        self,
        *,
        user_id: UUID,
        workflow_id: int,
    ) -> Workflow:
        workflow = self._session.get(Workflow, workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError("Workflow not found")

        if workflow.user_id != user_id:
            raise WorkflowAuthorizationError("Cannot run another user's workflow")

        if not can_transition_workflow(workflow.state, WorkflowState.QUEUED):
            raise WorkflowServiceError(
                f"Workflow cannot be queued from state '{workflow.state.value}'"
            )

        workflow.state = WorkflowState.QUEUED
        for task in workflow.tasks:
            if not can_transition_task(task.state, TaskState.QUEUED):
                raise WorkflowServiceError(
                    f"Task {task.id} cannot be queued from state '{task.state.value}'"
                )
            task.state = TaskState.QUEUED

        self._session.flush()
        self._session.refresh(workflow)
        self._session.refresh(workflow, attribute_names=["tasks"])
        return workflow


__all__ = [
    "WorkflowAuthorizationError",
    "WorkflowNotFoundError",
    "WorkflowService",
    "WorkflowServiceError",
    "WorkflowTemplateError",
]
