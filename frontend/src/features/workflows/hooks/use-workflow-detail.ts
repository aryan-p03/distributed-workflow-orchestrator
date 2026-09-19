import { useCallback, useEffect, useRef, useState } from "react"
import { getWorkflow, runWorkflow } from "../api/workflows.api"
import { isTerminal } from "../model/workflow.model"
import type { WorkflowDetail } from "../types/workflow.types"
import type { APIError } from "@/lib/api/errors"

const POLL_INTERVAL_MS = 2500

export function useWorkflowDetail(workflowId: number | null) {
  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null)
  // Initialize to false when there is no id to fetch; the effect will set it true then false on resolution.
  const [isLoading, setIsLoading] = useState(() => workflowId !== null)
  const [error, setError] = useState<APIError | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [runError, setRunError] = useState<APIError | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  // Ref tracks whether polling should fetch on each tick without causing effect re-runs.
  const pollActiveRef = useRef(false)

  useEffect(() => {
    if (workflowId === null) return // isLoading already false from initializer

    let isActive = true
    pollActiveRef.current = true

    async function fetchWorkflow() {
      try {
        const data = await getWorkflow(workflowId!)
        if (!isActive) return
        setWorkflow(data)
        setRefreshKey((current) => current + 1)
        setError(null)
        if (isTerminal(data.state)) {
          pollActiveRef.current = false
        }
      } catch (err) {
        if (!isActive) return
        setError(err as APIError)
        pollActiveRef.current = false
      } finally {
        if (isActive) setIsLoading(false)
      }
    }

    void fetchWorkflow()

    const intervalId = setInterval(() => {
      if (!pollActiveRef.current) return
      void fetchWorkflow()
    }, POLL_INTERVAL_MS)

    return () => {
      isActive = false
      pollActiveRef.current = false
      clearInterval(intervalId)
    }
  }, [workflowId])

  const run = useCallback(async () => {
    if (workflowId === null) return
    setIsRunning(true)
    setRunError(null)
    try {
      const data = await runWorkflow(workflowId)
      setWorkflow(data)
      setRefreshKey((current) => current + 1)
      if (!isTerminal(data.state)) {
        pollActiveRef.current = true
      }
    } catch (err) {
      setRunError(err as APIError)
    } finally {
      setIsRunning(false)
    }
  }, [workflowId])

  return { workflow, isLoading, error, run, isRunning, runError, refreshKey }
}
