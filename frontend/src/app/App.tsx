import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { AuthProvider } from "@/features/auth/context/auth-context"
import { AuthGuard } from "@/components/auth-guard"
import { LoginPage } from "@/features/auth/pages/login-page"
import { RegisterPage } from "@/features/auth/pages/register-page"
import { ProtectedLayout } from "./protected-layout"

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<AuthGuard />}>
            <Route element={<ProtectedLayout />}>
              <Route index element={<Navigate to="/workflows" replace />} />
              <Route
                path="/workflows"
                element={<div className="p-6 text-muted-foreground">Workflows — coming soon.</div>}
              />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
