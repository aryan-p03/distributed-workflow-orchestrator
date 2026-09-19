# Stale Task Recovery

The worker exposes `worker.recover_stale_tasks` to recover tasks left in `running` after a worker crash.

## Configuration

`TASK_RECOVERY_STALE_SECONDS` controls the age threshold. It defaults to `900` seconds and uses the task's `updated_at` timestamp.

## Manual Run

From the backend environment, run:

```bash
celery -A backend.worker.celery_app:celery_app call worker.recover_stale_tasks
```

The task locks eligible rows, changes them from `running` to `queued`, appends a warning log, commits the transaction, and republishes each recovered task.

## Scheduling

Run the recovery task at least once per stale threshold. For the default threshold, a five-minute cron schedule is suitable:

```cron
*/5 * * * * cd /path/to/distributed-workflow-orchestrator/backend && uv run celery -A backend.worker.celery_app:celery_app call worker.recover_stale_tasks
```

Recovery is idempotent for a task: once it is requeued, later sweeps will not select it again unless a worker claims it and it becomes stale again.