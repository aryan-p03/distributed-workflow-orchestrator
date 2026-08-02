import * as React from "react"

import { cn } from "@/lib/utils"

function Select({ className, children, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      data-slot="select"
      className={cn(
        "border-input bg-background ring-offset-background focus-visible:ring-ring flex h-9 w-full rounded-lg border px-3 py-2 text-sm outline-none focus-visible:ring-2",
        className
      )}
      {...props}
    >
      {children}
    </select>
  )
}

export { Select }
