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
        countdown_seconds: int | None = None,
    ) -> None:
        if countdown_seconds is None:
            enqueue_task_execution(task_id=task_id, payload=payload)
            return

        enqueue_task_execution(
            task_id=task_id,
            payload=payload,
            countdown_seconds=countdown_seconds,
        )


__all__ = ["CeleryTaskQueueDispatcher"]
