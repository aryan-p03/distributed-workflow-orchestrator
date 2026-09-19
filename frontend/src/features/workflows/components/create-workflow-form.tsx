import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import type { BaseSyntheticEvent } from "react"
import type { UseFormReturn } from "react-hook-form"
import type { CreateWorkflowSchema } from "../schemas/create-workflow.schema"
import type { WorkflowTemplateDefinition } from "../types/workflow.types"

interface CreateWorkflowFormProps {
  form: UseFormReturn<CreateWorkflowSchema>
  onSubmit: (event?: BaseSyntheticEvent) => Promise<void>
  serverError: string | null
  templates: WorkflowTemplateDefinition[]
  isLoadingTemplates: boolean
  isSubmitting: boolean
  selectedTemplate: WorkflowTemplateDefinition | null
}

export function CreateWorkflowForm({
  form,
  onSubmit,
  serverError,
  templates,
  isLoadingTemplates,
  isSubmitting,
  selectedTemplate,
}: CreateWorkflowFormProps) {
  const {
    register,
    formState: { errors },
  } = form

  return (
    <Card className="w-full max-w-3xl">
      <CardHeader>
        <CardTitle>Create Workflow</CardTitle>
        <CardDescription>Choose a template and fill required fields.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={(event) => void onSubmit(event)} noValidate className="space-y-4">
          {serverError && (
            <Alert variant="destructive">
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="template_name">Template</Label>
            <Select
              id="template_name"
              aria-invalid={!!errors.template_name}
              {...register("template_name")}
            >
              {templates.map((template) => (
                <option key={template.name} value={template.name}>
                  {template.label}
                </option>
              ))}
            </Select>
            {errors.template_name && (
              <p className="text-sm text-destructive">{errors.template_name.message}</p>
            )}
            {isLoadingTemplates && (
              <p className="text-sm text-muted-foreground">Loading templates...</p>
            )}
          </div>

          {selectedTemplate && (
            <div className="rounded-lg border bg-muted/30 p-3">
              <p className="text-sm text-muted-foreground">{selectedTemplate.description}</p>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="workflow_name">Workflow Name (Optional)</Label>
            <Input
              id="workflow_name"
              placeholder="My workflow"
              aria-invalid={!!errors.workflow_name}
              {...register("workflow_name")}
            />
            {errors.workflow_name && (
              <p className="text-sm text-destructive">{errors.workflow_name.message}</p>
            )}
          </div>

          {selectedTemplate?.fields.map((field) => {
            const fieldError = errors[field.key as keyof CreateWorkflowSchema]
            const FieldControl = field.control === "textarea" ? Textarea : Input
            return (
              <div key={field.key} className="space-y-1.5">
                <Label htmlFor={field.key}>{field.label}</Label>
                <FieldControl
                  id={field.key}
                  placeholder={field.placeholder}
                  aria-invalid={!!fieldError}
                  {...register(field.key)}
                />
                {fieldError && <p className="text-sm text-destructive">{fieldError.message}</p>}
              </div>
            )
          })}

          <Button type="submit" disabled={isSubmitting || isLoadingTemplates}>
            {isSubmitting ? "Creating workflow..." : "Create workflow"}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
