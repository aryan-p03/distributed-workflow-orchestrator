import { z } from "zod"

export const createWorkflowSchema = z
  .object({
    template_name: z.string().trim().min(1, "Template is required."),
    workflow_name: z.string().trim().max(120, "Workflow name is too long.").optional(),
  })
  .catchall(z.string().trim())

export type CreateWorkflowSchema = z.infer<typeof createWorkflowSchema>
