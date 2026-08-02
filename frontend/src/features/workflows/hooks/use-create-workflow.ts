import { useEffect, useMemo, useState } from "react"
import { useForm, useWatch } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useNavigate } from "react-router-dom"
import { createWorkflow, getWorkflowTemplates } from "../api/workflows.api"
import { createWorkflowSchema, type CreateWorkflowSchema } from "../schemas/create-workflow.schema"
import type { APIError } from "@/lib/api/errors"
import type { WorkflowTemplateDefinition } from "../types/workflow.types"

function buildPayload(data: CreateWorkflowSchema): Record<string, string> {
  const payload: Record<string, string> = {}
  const allFields: Array<keyof CreateWorkflowSchema> = [
    "workflow_name",
    "document_name",
    "source_uri",
    "destination_uri",
    "service_name",
    "release_version",
    "environment",
  ]

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
      template_name: "document_processing",
      workflow_name: "",
      document_name: "",
      source_uri: "",
      destination_uri: "",
      service_name: "",
      release_version: "",
      environment: "",
    },
  })

  const selectedTemplateName = useWatch({ control: form.control, name: "template_name" })

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
      } finally {
        setIsLoadingTemplates(false)
      }
    }

    void loadTemplates()
  }, [])

  async function onSubmit(data: CreateWorkflowSchema) {
    setServerError(null)

    try {
      const created = await createWorkflow({
        template_name: data.template_name,
        payload: buildPayload(data),
      })
      navigate(`/workflows/${created.id}`)
    } catch (err) {
      const apiErr = err as APIError
      if (apiErr.source?.type === "field") {
        form.setError(apiErr.source.name as keyof CreateWorkflowSchema, {
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
