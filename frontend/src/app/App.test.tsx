import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

// Minimal mocks for the full app tree
vi.mock("@/features/auth/context/auth-context", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock("@/features/auth/hooks/use-auth", () => ({
  useAuth: () => ({ status: "unauthenticated", user: null, refresh: vi.fn(), logout: vi.fn() }),
}))

import App from "./App"

describe("App", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/login")
  })

  it("renders the login page at /login", () => {
    render(<App />)
    expect(screen.getByText(/enter your credentials/i)).toBeInTheDocument()
  })

  it("renders the register page at /register", () => {
    window.history.pushState({}, "", "/register")
    render(<App />)
    expect(screen.getByText(/start managing workflows/i)).toBeInTheDocument()
  })
})
