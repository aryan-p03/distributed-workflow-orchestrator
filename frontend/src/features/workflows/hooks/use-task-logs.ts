import { useEffect, useState } from "react"
import { getTaskLogs } from "../api/workflows.api"
import type { TaskLog } from "../types/workflow.types"
import type { APIError } from "@/lib/api/errors"

export function useTaskLogs(workflowId: number, taskId: number, refreshKey: number) {
  const [logs, setLogs] = useState<TaskLog[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<APIError | null>(null)

  useEffect(() => {
    let isActive = true

    async function fetchLogs() {
      try {
        const response = await getTaskLogs(workflowId, taskId)
        if (!isActive) return
        setLogs(response.items)
        setError(null)
      } catch (err) {
        if (!isActive) return
        setError(err as APIError)
      } finally {
        if (isActive) setIsLoading(false)
      }
    }

    void fetchLogs()

    return () => {
      isActive = false
    }
  }, [workflowId, taskId, refreshKey])

  return { logs, isLoading, error }
}
