import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import App from "./App"

describe("App", () => {
  it("renders the title", () => {
    render(<App />)

    expect(screen.getByText("Distributed Workflow Orchestrator")).toBeInTheDocument()
  })

  it("increments the count on button click", async () => {
    const user = userEvent.setup()

    render(<App />)

    const button = screen.getByRole("button")

    await user.click(button)
    expect(button).toHaveTextContent("Clicked 1 time")

    await user.click(button)
    expect(button).toHaveTextContent("Clicked 2 times")
  })
})
