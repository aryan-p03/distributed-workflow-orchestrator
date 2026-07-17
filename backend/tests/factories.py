from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from backend.domain.workflow_state import TaskState, WorkflowState
from backend.infrastructure.db.models import Task, TaskLog, User, Workflow

_DEFAULT_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def create_user(
    session: Session,
    *,
    email: str = "user@example.com",
    username: str = "user",
    password_hash: str = "hashed-password",
    created_at: datetime = _DEFAULT_TIME,
) -> User:
    user = User(
        email=email,
        username=username,
        password_hash=password_hash,
        created_at=created_at,
    )
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


def create_workflow(
    session: Session,
    *,
    user_id: UUID,
    name: str = "Sample workflow",
    state: WorkflowState = WorkflowState.CREATED,
    created_at: datetime = _DEFAULT_TIME,
    updated_at: datetime = _DEFAULT_TIME,
) -> Workflow:
    workflow = Workflow(
        user_id=user_id,
        name=name,
        state=state,
        created_at=created_at,
        updated_at=updated_at,
    )
    session.add(workflow)
    session.flush()
    session.refresh(workflow)
    return workflow


def create_task(
    session: Session,
    *,
    workflow_id: int,
    name: str = "Sample task",
    task_type: str = "noop",
    state: TaskState = TaskState.CREATED,
    retry_count: int = 0,
    result: str | None = None,
    created_at: datetime = _DEFAULT_TIME,
    updated_at: datetime = _DEFAULT_TIME,
) -> Task:
    task = Task(
        workflow_id=workflow_id,
        name=name,
        task_type=task_type,
        state=state,
        retry_count=retry_count,
        result=result,
        created_at=created_at,
        updated_at=updated_at,
    )
    session.add(task)
    session.flush()
    session.refresh(task)
    return task


def create_task_log(
    session: Session,
    *,
    task_id: int,
    message: str = "Task created",
    level: str = "INFO",
    created_at: datetime = _DEFAULT_TIME,
) -> TaskLog:
    task_log = TaskLog(
        task_id=task_id,
        message=message,
        level=level,
        created_at=created_at,
    )
    session.add(task_log)
    session.flush()
    session.refresh(task_log)
    return task_log
