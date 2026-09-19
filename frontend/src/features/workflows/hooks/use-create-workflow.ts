import { useEffect, useMemo, useState } from "react"
import { useForm, useWatch } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useNavigate } from "react-router-dom"
import { createWorkflow, getWorkflowTemplates } from "../api/workflows.api"
import { createWorkflowSchema, type CreateWorkflowSchema } from "../schemas/create-workflow.schema"
import type { APIError } from "@/lib/api/errors"
import type { WorkflowTemplateDefinition } from "../types/workflow.types"

function buildPayload(
  data: CreateWorkflowSchema,
  template: WorkflowTemplateDefinition
): Record<string, string> {
  const payload: Record<string, string> = {}
  const allFields = ["workflow_name", ...template.fields.map((field) => field.key)]

  for (const key of allFields) {
    const value = data[key]
    if (typeof value === "string") {
      const trimmed = value.trim()
      if (trimmed.length > 0) {
        payload[key] = trimmed
      }
    }
  }

  return payload
}

export function useCreateWorkflow() {
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)
  const [templates, setTemplates] = useState<WorkflowTemplateDefinition[]>([])
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true)

  const form = useForm<CreateWorkflowSchema>({
    resolver: zodResolver(createWorkflowSchema),
    defaultValues: {
      template_name: "",
      workflow_name: "",
    },
  })

  const selectedTemplateName = useWatch({ control: form.control, name: "template_name" })
  const { getValues, setValue } = form

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.name === selectedTemplateName) ?? null,
    [templates, selectedTemplateName]
  )

  useEffect(() => {
    async function loadTemplates() {
      setIsLoadingTemplates(true)
      try {
        const nextTemplates = await getWorkflowTemplates()
        setTemplates(nextTemplates)
        if (!getValues("template_name") && nextTemplates[0]) {
          setValue("template_name", nextTemplates[0].name)
        }
        setServerError(null)
      } catch (err) {
        const apiErr = err as APIError
        setServerError(apiErr.description ?? "Failed to load workflow templates.")
      } finally {
        setIsLoadingTemplates(false)
      }
    }

    void loadTemplates()
  }, [getValues, setValue])

  async function onSubmit(data: CreateWorkflowSchema) {
    setServerError(null)

    if (selectedTemplate === null) {
      form.setError("template_name", { message: "Select a supported template." })
      return
    }

    let hasMissingField = false
    for (const field of selectedTemplate.fields) {
      const value = data[field.key]
      if (typeof value !== "string" || value.trim().length === 0) {
        form.setError(field.key, { message: "This field is required." })
        hasMissingField = true
      }
    }
    if (hasMissingField) return

    try {
      const created = await createWorkflow({
        template_name: data.template_name,
        payload: buildPayload(data, selectedTemplate),
      })
      navigate(`/workflows/${created.id}`)
    } catch (err) {
      const apiErr = err as APIError
      if (apiErr.source?.type === "field") {
        form.setError(apiErr.source.name, {
          message: apiErr.description,
        })
      } else {
        setServerError(apiErr.description ?? "Failed to create workflow.")
      }
    }
  }

  return {
    form,
    onSubmit: form.handleSubmit(onSubmit),
    serverError,
    templates,
    isLoadingTemplates,
    selectedTemplate,
    isSubmitting: form.formState.isSubmitting,
  }
}
