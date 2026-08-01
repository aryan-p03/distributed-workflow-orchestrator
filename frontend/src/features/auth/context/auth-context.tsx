import { createContext, useCallback, useEffect, useState } from "react"
import { me, logout as apiLogout } from "../api/auth.api"
import type { UserResponse } from "../types/auth.types"

export type AuthStatus = "checking" | "authenticated" | "unauthenticated"

export interface AuthContextValue {
  status: AuthStatus
  user: UserResponse | null
  refresh: () => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking")
  const [user, setUser] = useState<UserResponse | null>(null)

  const refresh = useCallback(async () => {
    setStatus("checking")
    try {
      const currentUser = await me()
      setUser(currentUser)
      setStatus("authenticated")
    } catch {
      setUser(null)
      setStatus("unauthenticated")
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } finally {
      setUser(null)
      setStatus("unauthenticated")
    }
  }, [])

  // Initial state is already "checking"; call me() directly to avoid a sync setState in the effect.
  useEffect(() => {
    me()
      .then((currentUser) => {
        setUser(currentUser)
        setStatus("authenticated")
      })
      .catch(() => {
        setStatus("unauthenticated")
      })
  }, [])

  return <AuthContext value={{ status, user, refresh, logout }}>{children}</AuthContext>
}
