from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Any, cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.application.services.task_execution_service import TaskExecutionService
from backend.application.services.workflow_progression_service import WorkflowProgressionService
from backend.infrastructure.config import get_settings
from backend.infrastructure.db.models import Task, TaskLog
from backend.worker.celery_app import celery_app
from backend.worker.handlers import dispatch_task_handler


@celery_app.task(name="worker.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    return "pong"


@celery_app.task(name="worker.execute_task")  # type: ignore[untyped-decorator]
def execute_task(
    task_id: int,
    payload: Mapping[str, object] | None = None,
) -> dict[str, Any]:
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

        try:
            handler_result = dispatch_task_handler(
                task_type=task.task_type,
                task_name=task.name,
                payload=payload,
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

        progression_service.apply_progression(workflow=task.workflow)
        session.commit()
        return result
    finally:
        session.close()


def _append_task_log(*, session: Session, task_id: int, message: str, level: str) -> None:
    session.add(TaskLog(task_id=task_id, message=message, level=level))


@lru_cache(maxsize=4)
def _get_session_factory(database_url: str) -> sessionmaker[Session]:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _new_session() -> Session:
    settings = get_settings()
    return _get_session_factory(settings.database_url)()
