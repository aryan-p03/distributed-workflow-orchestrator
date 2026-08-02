import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { WorkflowState } from "../types/workflow.types"

function normalizeState(value: string): string {
  return value.trim().toLowerCase()
}

const STATE_LABELS: Record<string, string> = {
  pending: "PENDING",
  created: "PENDING",
  queued: "PENDING",
  running: "RUNNING",
  completed: "COMPLETED",
  success: "COMPLETED",
  failed: "FAILED",
  cancelled: "CANCELLED",
}

export function WorkflowStatusBadge({ state }: { state: WorkflowState | string }) {
  const normalized = normalizeState(state)
  const label = STATE_LABELS[normalized] ?? state.toUpperCase()

  if (label === "PENDING") {
    return <Badge variant="secondary">{label}</Badge>
  }

  if (label === "RUNNING") {
    return <Badge variant="default">{label}</Badge>
  }

  if (label === "COMPLETED") {
    return (
      <Badge className={cn("bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200")}>
        {label}
      </Badge>
    )
  }

  if (label === "FAILED") {
    return <Badge variant="destructive">{label}</Badge>
  }

  return <Badge variant="outline">{label}</Badge>
}
