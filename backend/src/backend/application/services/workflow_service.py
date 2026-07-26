"""Workflow creation service backed by SQLAlchemy models."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from backend.application.services.task_dispatch_service import (
    TaskQueueDispatcher,
    WorkflowTaskDispatchService,
)
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
from backend.infrastructure.db.models import Task, TaskLog, User, Workflow


class WorkflowServiceError(ValueError):
    """Raised when workflow creation cannot proceed."""


class WorkflowNotFoundError(WorkflowServiceError):
    """Raised when a workflow cannot be found."""


class WorkflowAuthorizationError(WorkflowServiceError):
    """Raised when a workflow operation is attempted by a non-owner."""


class WorkflowTaskNotFoundError(WorkflowServiceError):
    """Raised when a task cannot be found inside a workflow."""


class WorkflowService:
    """Orchestrates workflow creation from predefined templates."""

    def __init__(
        self,
        session: Session,
        *,
        task_dispatcher: TaskQueueDispatcher | None = None,
    ) -> None:
        self._session = session
        self._dispatch_service = (
            WorkflowTaskDispatchService(task_dispatcher) if task_dispatcher is not None else None
        )
        if self._dispatch_service is not None and not self._session.info.get(
            "workflow_dispatch_hooks_installed", False
        ):
            event.listen(self._session, "after_commit", self._dispatch_after_commit)
            event.listen(self._session, "after_rollback", self._clear_pending_dispatches)
            self._session.info["workflow_dispatch_hooks_installed"] = True

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

        for task in workflow.tasks:
            if not can_transition_task(task.state, TaskState.QUEUED):
                raise WorkflowServiceError(
                    f"Task {task.id} cannot be queued from state '{task.state.value}'"
                )

        workflow.state = WorkflowState.QUEUED
        for task in workflow.tasks:
            task.state = TaskState.QUEUED

        self._session.flush()
        if self._dispatch_service is not None:
            first_task = self._dispatch_service.find_first_queued_task(workflow=workflow)
            if first_task is not None:
                self._enqueue_task_dispatch(task_id=first_task.id)
        self._session.refresh(workflow)
        self._session.refresh(workflow, attribute_names=["tasks"])
        return workflow

    def _enqueue_task_dispatch(self, *, task_id: int) -> None:
        pending = self._session.info.setdefault("workflow_pending_dispatch_task_ids", [])
        if task_id not in pending:
            pending.append(task_id)

    def _dispatch_after_commit(self, session: Session) -> None:
        if self._dispatch_service is None:
            return

        pending_task_ids = session.info.pop("workflow_pending_dispatch_task_ids", [])
        for task_id in pending_task_ids:
            self._dispatch_service.dispatch_task_by_id(task_id=task_id)

    def _clear_pending_dispatches(self, session: Session) -> None:
        session.info.pop("workflow_pending_dispatch_task_ids", None)

    def list_workflows(
        self,
        *,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Workflow]:
        return list(
            self._session.execute(
                select(Workflow)
                .where(Workflow.user_id == user_id)
                .order_by(Workflow.created_at.desc(), Workflow.id.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )

    def count_workflows(self, *, user_id: UUID) -> int:
        return int(
            self._session.execute(
                select(func.count()).select_from(Workflow).where(Workflow.user_id == user_id)
            ).scalar_one()
        )

    def get_workflow(self, *, user_id: UUID, workflow_id: int) -> Workflow:
        workflow = self._session.get(Workflow, workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError("Workflow not found")

        if workflow.user_id != user_id:
            raise WorkflowAuthorizationError("Cannot access another user's workflow")

        self._session.refresh(workflow, attribute_names=["tasks"])
        return workflow

    def get_task(
        self,
        *,
        user_id: UUID,
        workflow_id: int,
        task_id: int,
    ) -> Task:
        workflow = self.get_workflow(user_id=user_id, workflow_id=workflow_id)
        task = next((item for item in workflow.tasks if item.id == task_id), None)
        if task is None:
            raise WorkflowTaskNotFoundError("Task not found")
        return task

    def list_task_logs(
        self,
        *,
        user_id: UUID,
        workflow_id: int,
        task_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskLog]:
        task = self.get_task(user_id=user_id, workflow_id=workflow_id, task_id=task_id)
        return list(
            self._session.execute(
                select(TaskLog)
                .where(TaskLog.task_id == task.id)
                .order_by(TaskLog.created_at.asc(), TaskLog.id.asc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )

    def count_task_logs(self, *, user_id: UUID, workflow_id: int, task_id: int) -> int:
        task = self.get_task(user_id=user_id, workflow_id=workflow_id, task_id=task_id)
        return int(
            self._session.execute(
                select(func.count()).select_from(TaskLog).where(TaskLog.task_id == task.id)
            ).scalar_one()
        )


__all__ = [
    "WorkflowAuthorizationError",
    "WorkflowNotFoundError",
    "WorkflowService",
    "WorkflowServiceError",
    "WorkflowTaskNotFoundError",
    "WorkflowTemplateError",
]
