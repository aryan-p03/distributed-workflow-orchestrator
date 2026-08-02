import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"
import { WorkflowStatusBadge } from "./workflow-status-badge"

describe("WorkflowStatusBadge", () => {
  it("maps backend success state to COMPLETED label", () => {
    render(<WorkflowStatusBadge state="success" />)
    expect(screen.getByText("COMPLETED")).toBeInTheDocument()
  })

  it("renders FAILED label for failed state", () => {
    render(<WorkflowStatusBadge state="failed" />)
    expect(screen.getByText("FAILED")).toBeInTheDocument()
  })

  it("renders PENDING label for created state", () => {
    render(<WorkflowStatusBadge state="created" />)
    expect(screen.getByText("PENDING")).toBeInTheDocument()
  })
})
