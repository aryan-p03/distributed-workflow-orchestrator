import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import { WorkflowStatusBadge } from "./workflow-status-badge"

describe("WorkflowStatusBadge", () => {
  it("renders the backend SUCCESS label", () => {
    render(<WorkflowStatusBadge state="success" />)
    expect(screen.getByText("SUCCESS")).toBeInTheDocument()
  })

  it("renders FAILED label for failed state", () => {
    render(<WorkflowStatusBadge state="failed" />)
    expect(screen.getByText("FAILED")).toBeInTheDocument()
  })

  it("renders CREATED label for created state", () => {
    render(<WorkflowStatusBadge state="created" />)
    expect(screen.getByText("CREATED")).toBeInTheDocument()
  })
})
