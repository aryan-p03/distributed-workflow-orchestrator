import { act, renderHook, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { getTaskLogs } from "../api/workflows.api"
import type { TaskLogListResponse } from "../types/workflow.types"
import { useTaskLogs } from "./use-task-logs"

vi.mock("../api/workflows.api", () => ({
  getTaskLogs: vi.fn(),
}))

const initialResponse: TaskLogListResponse = {
  items: [
    {
      id: 1,
      task_id: 7,
      message: "Task execution started",
      level: "INFO",
      created_at: "2026-09-19T10:00:00Z",
    },
  ],
  limit: 50,
  offset: 0,
  total: 1,
}

const refreshedResponse: TaskLogListResponse = {
  ...initialResponse,
  items: [
    ...initialResponse.items,
    {
      id: 2,
      task_id: 7,
      message: "Task completed",
      level: "INFO",
      created_at: "2026-09-19T10:00:01Z",
    },
  ],
  total: 2,
}

afterEach(() => {
  vi.clearAllMocks()
})

describe("useTaskLogs", () => {
  it("refreshes logs when the workflow polling key changes", async () => {
    const getTaskLogsMock = vi.mocked(getTaskLogs)
    getTaskLogsMock.mockResolvedValueOnce(initialResponse).mockResolvedValueOnce(refreshedResponse)

    const { result, rerender } = renderHook(({ refreshKey }) => useTaskLogs(1, 7, refreshKey), {
      initialProps: { refreshKey: 1 },
    })

    await waitFor(() => expect(result.current.logs).toEqual(initialResponse.items))
    expect(getTaskLogsMock).toHaveBeenCalledTimes(1)

    await act(async () => {
      rerender({ refreshKey: 2 })
    })

    await waitFor(() => expect(result.current.logs).toEqual(refreshedResponse.items))
    expect(getTaskLogsMock).toHaveBeenCalledTimes(2)
    expect(result.current.error).toBeNull()
  })
})
