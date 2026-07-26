from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from backend.domain.workflow_state import TaskState, can_transition_task
from backend.infrastructure.db.models import Task


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_backoff_seconds: int = 5


@dataclass(frozen=True)
class TaskFailureResolution:
    result: dict[str, Any]
    retry_scheduled: bool
    backoff_seconds: int | None


class TaskExecutionService:
    """Applies task transitions, retry policy, and normalized result persistence."""

    def __init__(self, *, retry_policy: RetryPolicy = RetryPolicy()) -> None:
        self._retry_policy = retry_policy

    def mark_running(self, *, task: Task) -> None:
        if not can_transition_task(task.state, TaskState.RUNNING):
            raise ValueError(
                f"Task {task.id} cannot transition from '{task.state.value}' to running"
            )
        task.state = TaskState.RUNNING

    def complete_success(self, *, task: Task, result: dict[str, Any]) -> dict[str, Any]:
        if not can_transition_task(task.state, TaskState.SUCCESS):
            raise ValueError(
                f"Task {task.id} cannot transition from '{task.state.value}' to success"
            )
        task.state = TaskState.SUCCESS
        task.result = json.dumps(result)
        return result

    def complete_failure(
        self,
        *,
        task: Task,
        message: str,
        error_type: str,
    ) -> TaskFailureResolution:
        if not can_transition_task(task.state, TaskState.FAILED):
            raise ValueError(
                f"Task {task.id} cannot transition from '{task.state.value}' to failed"
            )

        attempt_number = task.retry_count + 1
        retry_scheduled = attempt_number < self._retry_policy.max_attempts
        backoff_seconds = (
            self._retry_policy.base_backoff_seconds * (2**task.retry_count)
            if retry_scheduled
            else None
        )

        result: dict[str, Any] = {
            "status": "failed",
            "message": message,
            "data": {
                "error_type": error_type,
                "attempt": attempt_number,
                "max_attempts": self._retry_policy.max_attempts,
                "retry_scheduled": retry_scheduled,
            },
        }

        task.state = TaskState.FAILED
        if retry_scheduled:
            if not can_transition_task(task.state, TaskState.RETRYING):
                raise ValueError(
                    f"Task {task.id} cannot transition from '{task.state.value}' to retrying"
                )
            task.state = TaskState.RETRYING
            task.retry_count += 1
            result["data"]["retry_count"] = task.retry_count
            result["data"]["next_backoff_seconds"] = backoff_seconds

            if not can_transition_task(task.state, TaskState.QUEUED):
                raise ValueError(
                    f"Task {task.id} cannot transition from '{task.state.value}' to queued"
                )
            task.state = TaskState.QUEUED
        else:
            result["data"]["retry_count"] = task.retry_count

        task.result = json.dumps(result)
        return TaskFailureResolution(
            result=result,
            retry_scheduled=retry_scheduled,
            backoff_seconds=backoff_seconds,
        )
