import { Outlet } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/features/auth/hooks/use-auth"

export function ProtectedLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-background px-6 py-3 flex items-center justify-between">
        <span className="font-semibold text-sm">Workflow Orchestrator</span>
        <div className="flex items-center gap-3">
          {user && <span className="text-sm text-muted-foreground">{user.username}</span>}
          <Button variant="ghost" size="sm" onClick={() => void logout()}>
            Sign out
          </Button>
        </div>
      </header>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}
