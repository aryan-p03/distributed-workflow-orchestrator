import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { AuthGuard } from "@/components/auth-guard"

const mockUseAuth = vi.fn()

vi.mock("@/features/auth/hooks/use-auth", () => ({
  useAuth: () => mockUseAuth(),
}))

function renderGuard(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login page</div>} />
        <Route element={<AuthGuard />}>
          <Route path="/" element={<div>Protected content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

describe("AuthGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows loading skeleton while checking", () => {
    mockUseAuth.mockReturnValue({ status: "checking" })
    renderGuard()
    // AuthLoading renders skeletons; no protected content yet
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument()
  })

  it("redirects to /login when unauthenticated", async () => {
    mockUseAuth.mockReturnValue({ status: "unauthenticated" })
    renderGuard()
    await waitFor(() => {
      expect(screen.getByText("Login page")).toBeInTheDocument()
    })
  })

  it("renders protected content when authenticated", () => {
    mockUseAuth.mockReturnValue({ status: "authenticated", user: { username: "alice" } })
    renderGuard()
    expect(screen.getByText("Protected content")).toBeInTheDocument()
  })
})
