import { get, post } from "@/lib/api/http"
import type {
  CreateWorkflowRequest,
  CreateWorkflowResponse,
  TaskLogListResponse,
  WorkflowDetail,
  WorkflowListResponse,
  WorkflowTemplateDefinition,
} from "../types/workflow.types"

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
  return get<WorkflowTemplateDefinition[]>("/workflows/templates")
}

export function getTaskLogs(workflowId: number, taskId: number): Promise<TaskLogListResponse> {
  return get<TaskLogListResponse>(`/workflows/${workflowId}/tasks/${taskId}/logs`)
}

export function runWorkflow(workflowId: number): Promise<WorkflowDetail> {
  return post<WorkflowDetail>(`/workflows/${workflowId}/run`)
}
