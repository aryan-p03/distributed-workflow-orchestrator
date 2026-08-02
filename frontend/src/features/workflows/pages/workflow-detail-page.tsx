import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { getWorkflow } from "../api/workflows.api"
import type { WorkflowDetail } from "../types/workflow.types"
import type { APIError } from "@/lib/api/errors"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { WorkflowStatusBadge } from "../components/workflow-status-badge"

export function WorkflowDetailPage() {
  const { workflowId } = useParams()
  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<APIError | null>(null)

  useEffect(() => {
    async function loadWorkflow() {
      setIsLoading(true)
      setError(null)

      const numericId = Number(workflowId)
      if (!Number.isFinite(numericId)) {
        setError({ code: "INVALID_ID", description: "Invalid workflow id." })
        setIsLoading(false)
        return
      }

      try {
        const response = await getWorkflow(numericId)
        setWorkflow(response)
      } catch (err) {
        setError(err as APIError)
      } finally {
        setIsLoading(false)
      }
    }

    void loadWorkflow()
  }, [workflowId])

  if (isLoading) {
    return (
      <main className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
      </main>
    )
  }

  if (error) {
    return (
      <main className="space-y-4">
        <Button asChild variant="outline">
          <Link to="/workflows" className="inline-flex items-center gap-2">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to dashboard
          </Link>
        </Button>
        <Alert variant="destructive">
          <AlertDescription>{error.description}</AlertDescription>
        </Alert>
      </main>
    )
  }

  if (!workflow) {
    return null
  }

  return (
    <main className="space-y-6" aria-labelledby="workflow-detail-title">
      <section className="flex items-center justify-between gap-4">
        <h1 id="workflow-detail-title" className="text-2xl font-semibold tracking-tight">
          {workflow.name}
        </h1>
        <Button asChild variant="outline">
          <Link to="/workflows" className="inline-flex items-center gap-2">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to dashboard
          </Link>
        </Button>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Workflow status</CardTitle>
          <CardDescription>Current execution state and task progression.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <WorkflowStatusBadge state={workflow.state} />
          <ul className="space-y-2" aria-label="Workflow tasks">
            {workflow.tasks.map((task) => (
              <li key={task.id} className="rounded-md border bg-muted/30 px-3 py-2">
                <p className="font-medium">
                  {task.sequence}. {task.name}
                </p>
                <p className="text-sm text-muted-foreground">
                  {task.task_type} - {task.state}
                </p>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </main>
  )
}
