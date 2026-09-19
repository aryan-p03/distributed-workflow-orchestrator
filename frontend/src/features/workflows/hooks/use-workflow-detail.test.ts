import { describe, expect, it, vi, afterEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { useWorkflowDetail } from "./use-workflow-detail"
import * as api from "../api/workflows.api"
import type { WorkflowDetail } from "../types/workflow.types"

const baseWorkflow: WorkflowDetail = {
  id: 1,
  user_id: "user-1",
  name: "Test Workflow",
  state: "running",
  created_at: "2026-08-02T10:00:00Z",
  updated_at: "2026-08-02T10:00:00Z",
  tasks: [],
}

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe("useWorkflowDetail", () => {
  it("fetches workflow on mount and surfaces it in state", async () => {
    vi.spyOn(api, "getWorkflow").mockResolvedValue(baseWorkflow)

    const { result } = renderHook(() => useWorkflowDetail(1))

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.workflow).toEqual(baseWorkflow)
    expect(result.current.error).toBeNull()
  })

  it("exposes an error when the fetch fails", async () => {
    vi.spyOn(api, "getWorkflow").mockRejectedValue({
      code: "NET_ERR",
      description: "Network error",
    })

    const { result } = renderHook(() => useWorkflowDetail(1))

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.error).toEqual({ code: "NET_ERR", description: "Network error" })
    expect(result.current.workflow).toBeNull()
  })

  it("does not fetch when workflowId is null", () => {
    const getWorkflowSpy = vi.spyOn(api, "getWorkflow")

    const { result } = renderHook(() => useWorkflowDetail(null))

    expect(result.current.isLoading).toBe(false)
    expect(getWorkflowSpy).not.toHaveBeenCalled()
  })

  it("calls runWorkflow and updates workflow state", async () => {
    const initial = { ...baseWorkflow, state: "success" as const }
    const afterRun = { ...baseWorkflow, state: "queued" as const }
    vi.spyOn(api, "getWorkflow").mockResolvedValue(initial)
    const runSpy = vi.spyOn(api, "runWorkflow").mockResolvedValue(afterRun)

    const { result } = renderHook(() => useWorkflowDetail(1))

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    await act(async () => {
      await result.current.run()
    })

    expect(runSpy).toHaveBeenCalledWith(1)
    expect(result.current.workflow?.state).toBe("queued")
    expect(result.current.isRunning).toBe(false)
  })

  it("sets runError when runWorkflow fails", async () => {
    vi.spyOn(api, "getWorkflow").mockResolvedValue({ ...baseWorkflow, state: "success" as const })
    vi.spyOn(api, "runWorkflow").mockRejectedValue({
      code: "CONFLICT",
      description: "Already running.",
    })

    const { result } = renderHook(() => useWorkflowDetail(1))

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    await act(async () => {
      await result.current.run()
    })

    expect(result.current.runError).toEqual({ code: "CONFLICT", description: "Already running." })
  })

  it("polls on interval while state is non-terminal", async () => {
    vi.useFakeTimers()
    const runningWorkflow = { ...baseWorkflow, state: "running" as const }
    const getWorkflowSpy = vi.spyOn(api, "getWorkflow").mockResolvedValue(runningWorkflow)

    renderHook(() => useWorkflowDetail(1))

    // Flush initial fetch
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(getWorkflowSpy).toHaveBeenCalledTimes(1)

    // Advance two poll intervals
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2500)
    })
    expect(getWorkflowSpy).toHaveBeenCalledTimes(2)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2500)
    })
    expect(getWorkflowSpy).toHaveBeenCalledTimes(3)
  })

  it("stops polling when workflow reaches a terminal state", async () => {
    vi.useFakeTimers()
    const completedWorkflow = { ...baseWorkflow, state: "success" as const }
    const getWorkflowSpy = vi.spyOn(api, "getWorkflow").mockResolvedValue(completedWorkflow)

    renderHook(() => useWorkflowDetail(1))

    // Flush initial fetch
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(getWorkflowSpy).toHaveBeenCalledTimes(1)

    // Advance several intervals — no additional fetches should occur
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000)
    })

    expect(getWorkflowSpy).toHaveBeenCalledTimes(1)
  })
})
