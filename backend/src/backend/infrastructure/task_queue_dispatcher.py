from __future__ import annotations

from collections.abc import Mapping

from backend.worker.celery_app import enqueue_task_execution


class CeleryTaskQueueDispatcher:
    """Infrastructure adapter for publishing workflow tasks to Celery."""

    def dispatch_task(
        self,
        *,
        task_id: int,
        payload: Mapping[str, object] | None = None,
    ) -> None:
        enqueue_task_execution(task_id=task_id, payload=payload)


__all__ = ["CeleryTaskQueueDispatcher"]
