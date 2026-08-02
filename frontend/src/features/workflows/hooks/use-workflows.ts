import { useCallback, useEffect, useState } from "react"
import { listWorkflows } from "../api/workflows.api"
import type { WorkflowSummary } from "../types/workflow.types"
import type { APIError } from "@/lib/api/errors"

export function useWorkflows() {
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<APIError | null>(null)

  const refresh = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await listWorkflows()
      setWorkflows(response.items)
    } catch (err) {
      setError(err as APIError)
      setWorkflows([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let isActive = true

    async function loadInitialWorkflows() {
      try {
        const response = await listWorkflows()
        if (!isActive) {
          return
        }
        setWorkflows(response.items)
      } catch (err) {
        if (!isActive) {
          return
        }
        setError(err as APIError)
        setWorkflows([])
      } finally {
        if (isActive) {
          setIsLoading(false)
        }
      }
    }

    void loadInitialWorkflows()

    return () => {
      isActive = false
    }
  }, [])

  return {
    workflows,
    isLoading,
    error,
    isEmpty: !isLoading && workflows.length === 0 && !error,
    refresh,
  }
}
