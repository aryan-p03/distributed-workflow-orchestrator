import { Navigate, Outlet } from "react-router-dom"
import { useAuth } from "@/features/auth/hooks/use-auth"
import { AuthLoading } from "./auth-loading"

export function AuthGuard() {
  const { status } = useAuth()

  if (status === "checking") return <AuthLoading />
  if (status === "unauthenticated") return <Navigate to="/login" replace />

  return <Outlet />
}
