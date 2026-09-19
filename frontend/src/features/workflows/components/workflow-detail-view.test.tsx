import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { WorkflowDetailView } from "./workflow-detail-view"

vi.mock("../hooks/use-task-logs", () => ({
  useTaskLogs: () => ({ logs: [], isLoading: false, error: null }),
}))

describe("WorkflowDetailView", () => {
  it("renders structured task results and disables rerunning terminal executions", () => {
    render(
      <WorkflowDetailView
        workflow={{
          id: 7,
          user_id: "user-1",
          name: "CSV summary",
          state: "success",
          created_at: "2026-09-19T10:00:00Z",
          updated_at: "2026-09-19T10:00:01Z",
          tasks: [
            {
              id: 9,
              sequence: 1,
              name: "Summarize submitted CSV",
              task_type: "csv_process",
              state: "success",
              retry_count: 0,
              result:
                '{"status":"success","message":"CSV processing complete","data":{"row_count":3,"column_count":2}}',
              created_at: "2026-09-19T10:00:00Z",
              updated_at: "2026-09-19T10:00:01Z",
            },
          ],
        }}
        onRun={vi.fn()}
        isRunning={false}
        runError={null}
        refreshKey={1}
      />
    )

    expect(screen.getByRole("button", { name: "Run workflow" })).toBeDisabled()
    expect(screen.getByText(/cannot be started again/i)).toBeInTheDocument()
    expect(screen.getByText(/"row_count": 3/)).toBeInTheDocument()
    expect(screen.getByText(/"column_count": 2/)).toBeInTheDocument()
  })
})
