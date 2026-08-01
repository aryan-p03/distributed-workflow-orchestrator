import { Skeleton } from "@/components/ui/skeleton"

export function AuthLoading() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-muted px-4">
      <div className="w-full max-w-sm space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-64" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </main>
  )
}
