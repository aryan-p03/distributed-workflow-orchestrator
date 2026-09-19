import { Link, useParams } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useWorkflowDetail } from "../hooks/use-workflow-detail"
import { WorkflowDetailView } from "../components/workflow-detail-view"

function WorkflowDetailSkeleton() {
  return (
    <div className="space-y-6" aria-label="Loading workflow detail">
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-56" />
          <Skeleton className="h-4 w-72 mt-1" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-8 w-20" />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-24" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    </div>
  )
}

export function WorkflowDetailPage() {
  const { workflowId } = useParams()
  const numericId = Number(workflowId)
  const validId = Number.isFinite(numericId) ? numericId : null

  const { workflow, isLoading, error, run, isRunning, runError, refreshKey } =
    useWorkflowDetail(validId)

  const backLink = (
    <Button asChild variant="outline" size="sm">
      <Link to="/workflows" className="inline-flex items-center gap-2">
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to dashboard
      </Link>
    </Button>
  )

  if (!validId) {
    return (
      <main className="space-y-4">
        {backLink}
        <Alert variant="destructive">
          <AlertDescription>Invalid workflow id.</AlertDescription>
        </Alert>
      </main>
    )
  }

  if (isLoading) {
    return (
      <main className="space-y-4">
        {backLink}
        <WorkflowDetailSkeleton />
      </main>
    )
  }

  if (error) {
    return (
      <main className="space-y-4">
        {backLink}
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
        {backLink}
      </section>

      <WorkflowDetailView
        workflow={workflow}
        onRun={() => void run()}
        isRunning={isRunning}
        runError={runError}
        refreshKey={refreshKey}
      />
    </main>
  )
}
