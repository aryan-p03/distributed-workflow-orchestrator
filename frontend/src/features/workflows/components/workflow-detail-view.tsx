import { Play } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { WorkflowStatusBadge } from "./workflow-status-badge"
import { TaskLogPanel } from "./task-log-panel"
import { isTerminal } from "../model/workflow.model"
import type { WorkflowDetail } from "../types/workflow.types"
import type { APIError } from "@/lib/api/errors"

interface WorkflowDetailViewProps {
  workflow: WorkflowDetail
  onRun: () => void
  isRunning: boolean
  runError: APIError | null
}

export function WorkflowDetailView({
  workflow,
  onRun,
  isRunning,
  runError,
}: WorkflowDetailViewProps) {
  // True when workflow is actively queued or running (not yet terminal, not in initial created state).
  const isProcessing = !isTerminal(workflow.state) && workflow.state !== "created"

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <CardTitle>{workflow.name}</CardTitle>
              <CardDescription>
                Workflow #{workflow.id} &middot; created{" "}
                {new Date(workflow.created_at).toLocaleString()}
              </CardDescription>
            </div>
            <WorkflowStatusBadge state={workflow.state} />
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {isProcessing && (
            <p className="text-xs text-muted-foreground animate-pulse">
              Live &mdash; polling for updates every 2.5 s
            </p>
          )}

          <Separator />

          <div className="flex items-center gap-3">
            <Button
              onClick={onRun}
              disabled={isRunning || isProcessing}
              size="sm"
              aria-label="Run workflow"
            >
              <Play className="size-4 mr-1.5" aria-hidden="true" />
              {isRunning ? "Starting…" : "Run"}
            </Button>

            {!isProcessing && !isRunning && (
              <p className="text-xs text-muted-foreground">
                Workflow is in a terminal state. Run to dispatch a fresh execution.
              </p>
            )}

            {isProcessing && (
              <p className="text-xs text-muted-foreground">
                Execution in progress &mdash; run is disabled while active.
              </p>
            )}
          </div>

          {runError && (
            <Alert variant="destructive">
              <AlertDescription>{runError.description}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Tasks</CardTitle>
          <CardDescription>Ordered task execution steps and their log output.</CardDescription>
        </CardHeader>
        <CardContent>
          <TaskLogPanel workflowId={workflow.id} tasks={workflow.tasks} />
        </CardContent>
      </Card>
    </div>
  )
}
