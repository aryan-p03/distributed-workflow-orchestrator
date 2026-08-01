import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { RegisterPage } from "@/features/auth/pages/register-page"

const mockRegister = vi.fn()
const mockApiLogin = vi.fn()
const mockRefresh = vi.fn()

vi.mock("@/features/auth/api/auth.api", () => ({
  register: (...args: unknown[]) => mockRegister(...args),
  login: (...args: unknown[]) => mockApiLogin(...args),
  me: vi.fn().mockResolvedValue({ id: "1", username: "alice", email: "a@b.com" }),
}))

vi.mock("@/features/auth/hooks/use-auth", () => ({
  useAuth: () => ({ status: "unauthenticated", user: null, refresh: mockRefresh, logout: vi.fn() }),
}))

function renderRegister() {
  return render(
    <MemoryRouter initialEntries={["/register"]}>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockRegister.mockResolvedValue({ id: "1", username: "alice", email: "a@b.com" })
    mockApiLogin.mockResolvedValue({ access_token: "tok" })
    mockRefresh.mockResolvedValue(undefined)
  })

  it("renders username, email and password fields", () => {
    renderRegister()
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it("shows validation errors when submitting empty form", async () => {
    const user = userEvent.setup()
    renderRegister()
    await user.click(screen.getByRole("button", { name: /create account/i }))
    await waitFor(() => {
      expect(screen.getByText(/username is required/i)).toBeInTheDocument()
    })
  })

  it("shows server error on conflict", async () => {
    const user = userEvent.setup()
    mockRegister.mockRejectedValue({ code: "API_ERROR", description: "Email already registered." })
    renderRegister()
    await user.type(screen.getByLabelText(/username/i), "alice")
    await user.type(screen.getByLabelText(/email/i), "exists@example.com")
    await user.type(screen.getByLabelText(/password/i), "password123")
    await user.click(screen.getByRole("button", { name: /create account/i }))
    await waitFor(() => {
      expect(screen.getByText(/email already registered/i)).toBeInTheDocument()
    })
  })
})
