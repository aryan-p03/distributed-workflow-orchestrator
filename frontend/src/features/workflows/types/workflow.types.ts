export type WorkflowState =
  | "created"
  | "queued"
  | "running"
  | "success"
  | "failed"
  | "pending"
  | "completed"
  | "cancelled"

export interface WorkflowSummary {
  id: number
  user_id: string
  name: string
  state: WorkflowState
  created_at: string
  updated_at: string
}

export interface WorkflowTask {
  id: number
  workflow_id?: number
  sequence: number
  name: string
  task_type: string
  state: string
  retry_count: number
  result: string | null
  created_at: string
  updated_at: string
}

export interface WorkflowDetail {
  id: number
  user_id: string
  name: string
  state: WorkflowState
  created_at: string
  updated_at: string
  tasks: WorkflowTask[]
}

export interface WorkflowListResponse {
  items: WorkflowSummary[]
  limit: number
  offset: number
  total: number
}

export interface CreateWorkflowRequest {
  template_name: string
  payload: Record<string, string>
}

export interface CreateWorkflowResponse {
  id: number
  user_id: string
  name: string
  state: WorkflowState
  created_at: string
  updated_at: string
  tasks: WorkflowTask[]
}

export interface TaskLog {
  id: number
  task_id: number
  message: string
  level: string
  created_at: string
}

export interface TaskLogListResponse {
  items: TaskLog[]
  limit: number
  offset: number
  total: number
}

export interface WorkflowTemplateField {
  key: string
  label: string
  placeholder: string
}

export interface WorkflowTemplateDefinition {
  name: string
  label: string
  description: string
  fields: WorkflowTemplateField[]
}
