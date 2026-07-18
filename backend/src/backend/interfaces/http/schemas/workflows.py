"""Pydantic schemas for workflow write endpoint payloads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateWorkflowRequest(BaseModel):
    template_name: str = Field(..., min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sequence: int
    name: str
    task_type: str
    state: str
    retry_count: int
    result: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    name: str
    state: str
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskResponse]
