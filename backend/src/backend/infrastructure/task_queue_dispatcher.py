from __future__ import annotations

from backend.worker.celery_app import enqueue_task_execution


class CeleryTaskQueueDispatcher:
    """Infrastructure adapter for publishing workflow tasks to Celery."""

    def dispatch_task(
        self,
        *,
        task_id: int,
        countdown_seconds: int | None = None,
    ) -> None:
        if countdown_seconds is None:
            enqueue_task_execution(task_id=task_id)
            return

        enqueue_task_execution(
            task_id=task_id,
            countdown_seconds=countdown_seconds,
        )


__all__ = ["CeleryTaskQueueDispatcher"]
