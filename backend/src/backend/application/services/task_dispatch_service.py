from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from backend.domain.workflow_state import TaskState
from backend.infrastructure.db.models import Task, Workflow


class TaskQueueDispatcher(Protocol):
    """Publishes a task identifier to the async execution queue."""

    def dispatch_task(
        self,
        *,
        task_id: int,
        payload: Mapping[str, object] | None = None,
    ) -> None:
        """Publish a runnable task to background execution."""


class WorkflowTaskDispatchService:
    """Chooses and dispatches the next runnable task in a workflow."""

    def __init__(self, dispatcher: TaskQueueDispatcher) -> None:
        self._dispatcher = dispatcher

    def dispatch_first_queued_task(self, *, workflow: Workflow) -> Task | None:
        for task in sorted(workflow.tasks, key=lambda item: item.sequence):
            if task.state != TaskState.QUEUED:
                continue
            self._dispatcher.dispatch_task(task_id=task.id, payload=None)
            return task
        return None


__all__ = [
    "TaskQueueDispatcher",
    "WorkflowTaskDispatchService",
]
