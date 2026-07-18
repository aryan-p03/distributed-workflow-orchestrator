"""Pydantic schemas for workflow read endpoint payloads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkflowListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    name: str
    state: str
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    items: list[WorkflowListItemResponse]
    limit: int
    offset: int
    total: int


class TaskReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    sequence: int
    name: str
    task_type: str
    state: str
    retry_count: int
    result: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowReadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    name: str
    state: str
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskReadResponse]


class TaskLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    message: str
    level: str
    created_at: datetime


class TaskLogListResponse(BaseModel):
    items: list[TaskLogResponse]
    limit: int
    offset: int
    total: int
