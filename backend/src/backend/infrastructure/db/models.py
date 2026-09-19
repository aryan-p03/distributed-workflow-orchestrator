from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from backend.domain.workflow_state import TaskState, WorkflowState


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    workflows: Mapped[list[Workflow]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (
        Index("ix_workflows_user_id", "user_id"),
        Index("ix_workflows_state", "state"),
        Index("ix_workflows_user_state", "user_id", "state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[WorkflowState] = mapped_column(
        Enum(WorkflowState, name="workflow_state"),
        default=WorkflowState.CREATED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="workflows")
    tasks: Mapped[list[Task]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="Task.sequence",
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_workflow_id", "workflow_id"),
        Index("ix_tasks_state", "state"),
        Index("ix_tasks_workflow_state", "workflow_id", "state"),
        CheckConstraint("retry_count >= 0", name="ck_tasks_retry_count_non_negative"),
        CheckConstraint("sequence >= 1", name="ck_tasks_sequence_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    input_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    state: Mapped[TaskState] = mapped_column(
        Enum(TaskState, name="task_state"),
        default=TaskState.CREATED,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    workflow: Mapped[Workflow] = relationship(back_populates="tasks")
    task_logs: Mapped[list[TaskLog]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class TaskLog(Base):
    __tablename__ = "task_logs"
    __table_args__ = (
        Index("ix_task_logs_task_id", "task_id"),
        Index("ix_task_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    task: Mapped[Task] = relationship(back_populates="task_logs")
