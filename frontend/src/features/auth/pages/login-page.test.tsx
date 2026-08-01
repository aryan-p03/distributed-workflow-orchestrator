import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { LoginPage } from "@/features/auth/pages/login-page"

const mockLogin = vi.fn()
const mockRefresh = vi.fn()

vi.mock("@/features/auth/api/auth.api", () => ({
  login: (...args: unknown[]) => mockLogin(...args),
  me: vi.fn().mockResolvedValue({ id: "1", username: "alice", email: "a@b.com" }),
}))

vi.mock("@/features/auth/hooks/use-auth", () => ({
  useAuth: () => ({ status: "authenticated", user: null, refresh: mockRefresh, logout: vi.fn() }),
}))

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLogin.mockResolvedValue({ access_token: "tok" })
    mockRefresh.mockResolvedValue(undefined)
  })

  it("renders email and password fields", () => {
    renderLogin()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it("shows validation error when submitting empty form", async () => {
    const user = userEvent.setup()
    renderLogin()
    await user.click(screen.getByRole("button", { name: /sign in/i }))
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    })
  })

  it("shows server error on failed login", async () => {
    const user = userEvent.setup()
    mockLogin.mockRejectedValue({ code: "UNAUTHORIZED", description: "Invalid credentials." })
    renderLogin()
    await user.type(screen.getByLabelText(/email/i), "bad@example.com")
    await user.type(screen.getByLabelText(/password/i), "wrongpass")
    await user.click(screen.getByRole("button", { name: /sign in/i }))
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })
})
