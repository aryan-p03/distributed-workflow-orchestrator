from __future__ import annotations

from backend.domain.workflow_state import (
    TaskState,
    WorkflowState,
    can_transition_workflow,
)
from backend.infrastructure.db.models import Workflow


class WorkflowProgressionService:
    """Computes and applies workflow progression based on task outcomes."""

    def apply_progression(self, *, workflow: Workflow) -> WorkflowState:
        target_state = self._compute_target_state(workflow=workflow)
        if workflow.state == target_state:
            return workflow.state

        if can_transition_workflow(workflow.state, target_state):
            workflow.state = target_state

        return workflow.state

    def _compute_target_state(self, *, workflow: Workflow) -> WorkflowState:
        task_states = [task.state for task in workflow.tasks]
        if task_states and all(state == TaskState.SUCCESS for state in task_states):
            return WorkflowState.SUCCESS

        if any(state == TaskState.FAILED for state in task_states):
            return WorkflowState.FAILED

        if any(state == TaskState.RUNNING for state in task_states):
            return WorkflowState.RUNNING

        if any(
            state in {TaskState.QUEUED, TaskState.RETRYING, TaskState.CREATED}
            for state in task_states
        ):
            if workflow.state == WorkflowState.RUNNING:
                return WorkflowState.RUNNING
            return WorkflowState.QUEUED

        return workflow.state
