# State Machine Baseline

## Scope

This baseline defines workflow and task transition contracts.
It describes how state transitions are modeled in the domain and application layers.

## Workflow States

- `created`
- `queued`
- `running`
- `success`
- `failed`

## Task States

- `created`
- `queued`
- `running`
- `success`
- `failed`
- `retrying`

## Workflow Transition Rules

- `created -> queued`
- `queued -> running`
- `running -> success`
- `running -> failed`

Illegal examples:

- `success -> running`
- `failed -> queued`
- `created -> success`

## Task Transition Rules

- `created -> queued`
- `queued -> running`
- `running -> success`
- `running -> failed`
- `failed -> retrying` (when retry budget remains)
- `retrying -> queued`

Illegal examples:

- `success -> running`
- `failed -> success` (without explicit retry cycle)

## Retry Semantics

- Retry budget is finite (target: 3 attempts).
- Backoff strategy is deterministic and centrally configured.
- Retry exhaustion forces terminal `failed` state.

## Terminal Semantics

Terminal states:

- task: `success`, `failed`
- workflow: `success`, `failed`

Rules:

- terminal states cannot transition to non-terminal states
- rerun requests for terminal tasks resolve to no-op/rejection behavior

## Transition Logging Contract

State changes are represented as append-only log entries with:

- `entity_type` (`workflow` or `task`)
- `entity_id`
- `from_state`
- `to_state`
- `reason`
- `triggered_by` (`api`, `worker`, `system`)
- `occurred_at`

## Invariants for Tests

- no illegal transition is persisted
- duplicate worker delivery does not cause duplicate terminal progression
- workflow terminal state is consistent with final task outcomes
- retry count monotonically increases and never exceeds configured max
