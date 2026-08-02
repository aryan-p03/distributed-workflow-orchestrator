import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { WorkflowTable } from "./workflow-table"
import type { APIError } from "@/lib/api/errors"

describe("WorkflowTable", () => {
  it("shows empty state inside the table body", () => {
    render(
      <MemoryRouter>
        <WorkflowTable workflows={[]} isLoading={false} isEmpty={true} error={null} />
      </MemoryRouter>
    )

    expect(screen.getByText(/no workflows yet/i)).toBeInTheDocument()
  })

  it("shows error state inside the table body", () => {
    const error: APIError = { code: "ERR", description: "Failed to load workflows." }

    render(
      <MemoryRouter>
        <WorkflowTable workflows={[]} isLoading={false} isEmpty={false} error={error} />
      </MemoryRouter>
    )

    expect(screen.getByText("Failed to load workflows.")).toBeInTheDocument()
  })

  it("renders workflow rows with detail links", () => {
    render(
      <MemoryRouter>
        <WorkflowTable
          isLoading={false}
          isEmpty={false}
          error={null}
          workflows={[
            {
              id: 12,
              user_id: "u-1",
              name: "Deploy billing",
              state: "running",
              created_at: "2026-08-02T12:00:00Z",
              updated_at: "2026-08-02T12:01:00Z",
            },
          ]}
        />
      </MemoryRouter>
    )

    expect(screen.getByRole("link", { name: "Deploy billing" })).toHaveAttribute(
      "href",
      "/workflows/12"
    )
  })
})
