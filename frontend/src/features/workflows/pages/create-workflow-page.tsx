import { ArrowLeft } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { useCreateWorkflow } from "../hooks/use-create-workflow"
import { CreateWorkflowForm } from "../components/create-workflow-form"

export function CreateWorkflowPage() {
  const {
    form,
    onSubmit,
    serverError,
    templates,
    isLoadingTemplates,
    selectedTemplate,
    isSubmitting,
  } = useCreateWorkflow()

  return (
    <main className="space-y-6" aria-labelledby="create-workflow-title">
      <section className="flex items-center justify-between gap-4">
        <div>
          <h1 id="create-workflow-title" className="text-2xl font-semibold tracking-tight">
            New Workflow
          </h1>
          <p className="text-sm text-muted-foreground">
            Create a workflow from a supported template.
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/workflows" className="inline-flex items-center gap-2">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to dashboard
          </Link>
        </Button>
      </section>

      <section>
        <CreateWorkflowForm
          form={form}
          onSubmit={onSubmit}
          serverError={serverError}
          templates={templates}
          isLoadingTemplates={isLoadingTemplates}
          isSubmitting={isSubmitting}
          selectedTemplate={selectedTemplate}
        />
      </section>
    </main>
  )
}
