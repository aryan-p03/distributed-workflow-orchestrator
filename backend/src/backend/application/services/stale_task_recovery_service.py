from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.workflow_state import TaskState, can_recover_task
from backend.infrastructure.db.models import Task, TaskLog


class StaleTaskRecoveryService:
    """Requeues tasks left running after a worker crash."""

    def __init__(self, session: Session, *, stale_after_seconds: int) -> None:
        if stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        self._session = session
        self._stale_after_seconds = stale_after_seconds

    def recover(self, *, now: datetime | None = None) -> list[int]:
        recovery_time = now or datetime.now(UTC)
        stale_before = recovery_time - timedelta(seconds=self._stale_after_seconds)
        tasks = self._session.scalars(
            select(Task)
            .where(Task.state == TaskState.RUNNING, Task.updated_at < stale_before)
            .with_for_update(skip_locked=True)
        ).all()

        recovered_task_ids: list[int] = []
        for task in tasks:
            if not can_recover_task(task.state, TaskState.QUEUED):
                continue
            task.state = TaskState.QUEUED
            self._session.add(
                TaskLog(
                    task_id=task.id,
                    level="WARNING",
                    message="Task recovered from stale running state and requeued",
                )
            )
            recovered_task_ids.append(task.id)

        self._session.flush()
        return recovered_task_ids


__all__ = ["StaleTaskRecoveryService"]
