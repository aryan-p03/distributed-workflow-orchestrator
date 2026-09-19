import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { WorkflowState } from "../types/workflow.types"

function normalizeState(value: string): string {
  return value.trim().toLowerCase()
}

export function WorkflowStatusBadge({ state }: { state: WorkflowState | string }) {
  const normalized = normalizeState(state)
  const label = normalized.toUpperCase()

  if (normalized === "created" || normalized === "queued") {
    return <Badge variant="secondary">{label}</Badge>
  }

  if (normalized === "running") {
    return <Badge variant="default">{label}</Badge>
  }

  if (normalized === "success") {
    return (
      <Badge className={cn("bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200")}>
        {label}
      </Badge>
    )
  }

  if (normalized === "failed") {
    return <Badge variant="destructive">{label}</Badge>
  }

  return <Badge variant="outline">{label}</Badge>
}
