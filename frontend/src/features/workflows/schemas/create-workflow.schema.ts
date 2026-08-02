import { z } from "zod"

const templateNames = ["document_processing", "release_pipeline"] as const

export const createWorkflowSchema = z
  .object({
    template_name: z.enum(templateNames, {
      error: "Template is required.",
    }),
    workflow_name: z.string().trim().max(120, "Workflow name is too long.").optional(),
    document_name: z.string().trim().optional(),
    source_uri: z.string().trim().optional(),
    destination_uri: z.string().trim().optional(),
    service_name: z.string().trim().optional(),
    release_version: z.string().trim().optional(),
    environment: z.string().trim().optional(),
  })
  .superRefine((value, ctx) => {
    const requiredByTemplate: Record<string, (keyof CreateWorkflowSchema)[]> = {
      document_processing: ["document_name", "source_uri", "destination_uri"],
      release_pipeline: ["service_name", "release_version", "environment"],
    }

    const requiredFields = requiredByTemplate[value.template_name] ?? []
    for (const field of requiredFields) {
      const fieldValue = value[field]
      if (!fieldValue || !fieldValue.trim()) {
        ctx.addIssue({
          code: "custom",
          path: [field],
          message: "This field is required.",
        })
      }
    }
  })

export type CreateWorkflowSchema = z.infer<typeof createWorkflowSchema>
