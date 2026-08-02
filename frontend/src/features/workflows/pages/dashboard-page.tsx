import { Link } from "react-router-dom"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useWorkflows } from "../hooks/use-workflows"
import { WorkflowTable, WorkflowTableLoadingCaption } from "../components/workflow-table"

export function DashboardPage() {
  const { workflows, isLoading, isEmpty, error } = useWorkflows()

  return (
    <main className="space-y-6" aria-labelledby="dashboard-title">
      <section className="flex items-center justify-between gap-4">
        <div>
          <h1 id="dashboard-title" className="text-2xl font-semibold tracking-tight">
            Workflows
          </h1>
          <p className="text-sm text-muted-foreground">
            Track workflow state and open details for each execution plan.
          </p>
        </div>
        <Button asChild>
          <Link to="/workflows/new" className="inline-flex items-center gap-2">
            <Plus className="size-4" aria-hidden="true" />
            New workflow
          </Link>
        </Button>
      </section>

      <section aria-label="Workflow list">
        <Card>
          <CardHeader>
            <CardTitle>Recent workflows</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading && <WorkflowTableLoadingCaption />}
            <WorkflowTable
              workflows={workflows}
              isLoading={isLoading}
              isEmpty={isEmpty}
              error={error}
            />
          </CardContent>
        </Card>
      </section>
    </main>
  )
}
