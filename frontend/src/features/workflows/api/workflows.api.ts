import { get, post } from "@/lib/api/http"
import type {
  CreateWorkflowRequest,
  CreateWorkflowResponse,
  TaskLogListResponse,
  WorkflowDetail,
  WorkflowListResponse,
  WorkflowTemplateDefinition,
} from "../types/workflow.types"

const WORKFLOW_TEMPLATES: WorkflowTemplateDefinition[] = [
  {
    name: "document_processing",
    label: "Document Processing",
    description: "Fetches, transforms, and publishes a document artifact.",
    fields: [
      { key: "document_name", label: "Document Name", placeholder: "Quarterly report" },
      { key: "source_uri", label: "Source URI", placeholder: "s3://incoming/reports/q1.pdf" },
      {
        key: "destination_uri",
        label: "Destination URI",
        placeholder: "s3://processed/reports/q1.json",
      },
    ],
  },
  {
    name: "release_pipeline",
    label: "Release Pipeline",
    description: "Validates, deploys, and smoke-tests a software release.",
    fields: [
      { key: "service_name", label: "Service Name", placeholder: "billing-api" },
      { key: "release_version", label: "Release Version", placeholder: "2026.08.0" },
      { key: "environment", label: "Environment", placeholder: "production" },
    ],
  },
]

export function listWorkflows(): Promise<WorkflowListResponse> {
  return get<WorkflowListResponse>("/workflows")
}

export function getWorkflow(workflowId: number): Promise<WorkflowDetail> {
  return get<WorkflowDetail>(`/workflows/${workflowId}`)
}

export function createWorkflow(body: CreateWorkflowRequest): Promise<CreateWorkflowResponse> {
  return post<CreateWorkflowResponse, CreateWorkflowRequest>("/workflows", body)
}

export function getWorkflowTemplates(): Promise<WorkflowTemplateDefinition[]> {
  return Promise.resolve(WORKFLOW_TEMPLATES)
}

export function getTaskLogs(workflowId: number, taskId: number): Promise<TaskLogListResponse> {
  return get<TaskLogListResponse>(`/workflows/${workflowId}/tasks/${taskId}/logs`)
}

export function runWorkflow(workflowId: number): Promise<WorkflowDetail> {
  return post<WorkflowDetail>(`/workflows/${workflowId}/run`)
}
