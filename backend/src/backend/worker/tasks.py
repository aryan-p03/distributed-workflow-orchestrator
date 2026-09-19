from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.application.services.stale_task_recovery_service import StaleTaskRecoveryService
from backend.application.services.task_execution_service import TaskExecutionService
from backend.application.services.workflow_progression_service import WorkflowProgressionService
from backend.domain.workflow_state import TaskState
from backend.infrastructure.config import get_settings
from backend.infrastructure.db.models import Task, TaskLog, Workflow
from backend.worker.celery_app import celery_app, enqueue_task_execution
from backend.worker.handlers import dispatch_task_handler


@celery_app.task(name="worker.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    return "pong"


@celery_app.task(name="worker.recover_stale_tasks")  # type: ignore[untyped-decorator]
def recover_stale_tasks() -> dict[str, Any]:
    settings = get_settings()
    session: Session = _new_session()
    try:
        recovery_service = StaleTaskRecoveryService(
            session,
            stale_after_seconds=settings.task_recovery_stale_seconds,
        )
        recovered_task_ids = recovery_service.recover(now=datetime.now(UTC))
        session.commit()
        for task_id in recovered_task_ids:
            enqueue_task_execution(task_id=task_id)
        return {"status": "success", "recovered_task_ids": recovered_task_ids}
    finally:
        session.close()


@celery_app.task(name="worker.execute_task")  # type: ignore[untyped-decorator]
def execute_task(task_id: int) -> dict[str, Any]:
    session: Session = _new_session()
    try:
        execution_service = TaskExecutionService()
        progression_service = WorkflowProgressionService()

        task = session.get(Task, task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        execution_service.mark_running(task=task)
        progression_service.apply_progression(workflow=task.workflow)
        _append_task_log(
            session=session,
            task_id=task.id,
            level="INFO",
            message="Task execution started",
        )
        session.flush()
        result: dict[str, Any]
        resolution = None

        try:
            handler_result = dispatch_task_handler(
                task_type=task.task_type,
                task_name=task.name,
                payload=task.input_payload,
            )
            result = cast(dict[str, Any], handler_result)
            result = execution_service.complete_success(task=task, result=result)
            _append_task_log(
                session=session,
                task_id=task.id,
                level="INFO",
                message=result["message"],
            )
        except Exception as exc:  # noqa: BLE001
            resolution = execution_service.complete_failure(
                task=task,
                message=str(exc),
                error_type=exc.__class__.__name__,
            )
            result = resolution.result

            if resolution.retry_scheduled:
                _append_task_log(
                    session=session,
                    task_id=task.id,
                    level="WARNING",
                    message=(
                        f"Task failed (attempt {result['data']['attempt']}/"
                        f"{result['data']['max_attempts']}); retry in "
                        f"{resolution.backoff_seconds} second(s)"
                    ),
                )
            else:
                _append_task_log(
                    session=session,
                    task_id=task.id,
                    level="ERROR",
                    message=result["message"],
                )

        workflow_state = progression_service.apply_progression(workflow=task.workflow)
        if not progression_service.is_terminal_state(workflow_state):
            if resolution is not None and resolution.retry_scheduled and resolution.backoff_seconds:
                enqueue_task_execution(
                    task_id=task.id,
                    countdown_seconds=resolution.backoff_seconds,
                )
            elif result["status"] == "success":
                next_task = _find_first_queued_task(workflow=task.workflow)
                if next_task is not None:
                    enqueue_task_execution(task_id=next_task.id)

        session.commit()
        return result
    finally:
        session.close()


def _append_task_log(*, session: Session, task_id: int, message: str, level: str) -> None:
    session.add(TaskLog(task_id=task_id, message=message, level=level))


def _find_first_queued_task(*, workflow: Workflow) -> Task | None:
    for queued_task in sorted(workflow.tasks, key=lambda item: item.sequence):
        if queued_task.state == TaskState.QUEUED:
            return queued_task
    return None


@lru_cache(maxsize=4)
def _get_session_factory(database_url: str) -> sessionmaker[Session]:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _new_session() -> Session:
    settings = get_settings()
    return _get_session_factory(settings.database_url)()
