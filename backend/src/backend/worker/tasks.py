from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.domain.workflow_state import TaskState, can_transition_task
from backend.infrastructure.config import get_settings
from backend.infrastructure.db.models import Task, TaskLog
from backend.worker.celery_app import celery_app
from backend.worker.handlers import HandlerResult, dispatch_task_handler


@celery_app.task(name="worker.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    return "pong"


@celery_app.task(name="worker.execute_task")  # type: ignore[untyped-decorator]
def execute_task(
    task_id: int,
    payload: Mapping[str, object] | None = None,
) -> HandlerResult:
    session: Session = _new_session()
    try:
        task = session.get(Task, task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        if not can_transition_task(task.state, TaskState.RUNNING):
            raise ValueError(
                f"Task {task.id} cannot transition from '{task.state.value}' to running"
            )

        task.state = TaskState.RUNNING
        _append_task_log(
            session=session,
            task_id=task.id,
            level="INFO",
            message="Task execution started",
        )
        session.flush()

        try:
            result = dispatch_task_handler(
                task_type=task.task_type,
                task_name=task.name,
                payload=payload,
            )
            task.state = TaskState.SUCCESS
            _append_task_log(
                session=session,
                task_id=task.id,
                level="INFO",
                message=result["message"],
            )
        except Exception as exc:  # noqa: BLE001
            result = {
                "status": "failed",
                "message": str(exc),
                "data": {"error_type": exc.__class__.__name__},
            }
            task.state = TaskState.FAILED
            _append_task_log(
                session=session,
                task_id=task.id,
                level="ERROR",
                message=result["message"],
            )

        task.result = json.dumps(result)
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
