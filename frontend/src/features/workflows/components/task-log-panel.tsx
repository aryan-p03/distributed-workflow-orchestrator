import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { useTaskLogs } from "../hooks/use-task-logs"
import { WorkflowStatusBadge } from "./workflow-status-badge"
import type { WorkflowTask } from "../types/workflow.types"

function formatTaskResult(result: string): string {
  try {
    const parsed = JSON.parse(result) as unknown
    return JSON.stringify(parsed, null, 2)
  } catch {
    return result
  }
}

function TaskLogSection({
  workflowId,
  task,
  refreshKey,
}: {
  workflowId: number
  task: WorkflowTask
  refreshKey: number
}) {
  const { logs, isLoading, error } = useTaskLogs(workflowId, task.id, refreshKey)

  return (
    <li className="rounded-md border bg-muted/30 px-3 py-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium text-sm">
          {task.sequence}. {task.name}
        </p>
        <WorkflowStatusBadge state={task.state} />
      </div>
      <p className="text-xs text-muted-foreground">{task.task_type}</p>

      {task.result && (
        <div className="space-y-1 rounded-md border bg-background p-3">
          <p className="text-xs font-medium">Result</p>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words text-xs font-mono">
            {formatTaskResult(task.result)}
          </pre>
        </div>
      )}

      {isLoading && (
        <div className="space-y-1 pt-1" aria-label="Loading task logs">
          <Skeleton className="h-3 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      )}

      {!isLoading && error && <p className="text-xs text-destructive">Unable to load logs.</p>}

      {!isLoading && !error && logs.length === 0 && (
        <p className="text-xs text-muted-foreground italic">No log entries.</p>
      )}

      {!isLoading && !error && logs.length > 0 && (
        <ul
          className="space-y-1 border-l-2 border-muted pl-3"
          aria-label={`Log entries for ${task.name}`}
        >
          {logs.map((log) => (
            <li key={log.id} className="flex gap-2 items-baseline">
              <span
                className={cn(
                  "text-xs font-mono shrink-0",
                  log.level === "ERROR" && "text-destructive",
                  log.level === "WARNING" && "text-yellow-600 dark:text-yellow-400",
                  log.level === "INFO" && "text-muted-foreground"
                )}
              >
                [{log.level}]
              </span>
              <span className="text-xs font-mono text-foreground break-all">{log.message}</span>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

export function TaskLogPanel({
  workflowId,
  tasks,
  refreshKey,
}: {
  workflowId: number
  tasks: WorkflowTask[]
  refreshKey: number
}) {
  if (tasks.length === 0) {
    return <p className="text-sm text-muted-foreground">No tasks found for this workflow.</p>
  }

  const sorted = [...tasks].sort((a, b) => a.sequence - b.sequence)

  return (
    <ul className="space-y-3" aria-label="Workflow tasks and logs">
      {sorted.map((task) => (
        <TaskLogSection key={task.id} workflowId={workflowId} task={task} refreshKey={refreshKey} />
      ))}
    </ul>
  )
}
