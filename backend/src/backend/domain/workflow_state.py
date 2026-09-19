from __future__ import annotations

import enum


class WorkflowState(enum.StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TaskState(enum.StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


_WORKFLOW_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.CREATED: {WorkflowState.QUEUED},
    WorkflowState.QUEUED: {WorkflowState.RUNNING},
    WorkflowState.RUNNING: {WorkflowState.SUCCESS, WorkflowState.FAILED},
    WorkflowState.SUCCESS: set(),
    WorkflowState.FAILED: set(),
}


_TASK_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.CREATED: {TaskState.QUEUED},
    TaskState.QUEUED: {TaskState.RUNNING},
    TaskState.RUNNING: {TaskState.SUCCESS, TaskState.FAILED},
    TaskState.FAILED: {TaskState.RETRYING},
    TaskState.RETRYING: {TaskState.QUEUED},
    TaskState.SUCCESS: set(),
}


def can_transition_workflow(current: WorkflowState, target: WorkflowState) -> bool:
    return target in _WORKFLOW_TRANSITIONS[current]


def can_transition_task(current: TaskState, target: TaskState) -> bool:
    return target in _TASK_TRANSITIONS[current]


def can_recover_task(current: TaskState, target: TaskState) -> bool:
    return current == TaskState.RUNNING and target == TaskState.QUEUED
