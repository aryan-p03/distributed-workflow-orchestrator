import { Link } from "react-router-dom"
import { Loader2 } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Skeleton } from "@/components/ui/skeleton"
import type { APIError } from "@/lib/api/errors"
import type { WorkflowSummary } from "../types/workflow.types"
import { WorkflowStatusBadge } from "./workflow-status-badge"

function formatDate(isoDate: string): string {
  const date = new Date(isoDate)
  return Number.isNaN(date.getTime()) ? isoDate : date.toLocaleString()
}

interface WorkflowTableProps {
  workflows: WorkflowSummary[]
  isLoading: boolean
  isEmpty: boolean
  error: APIError | null
}

export function WorkflowTable({ workflows, isLoading, isEmpty, error }: WorkflowTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Created</TableHead>
          <TableHead>Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isLoading &&
          Array.from({ length: 4 }).map((_, index) => (
            <TableRow key={`loading-row-${index}`}>
              <TableCell>
                <Skeleton className="h-4 w-48" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-5 w-24" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-36" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4 w-36" />
              </TableCell>
            </TableRow>
          ))}

        {!isLoading && error && (
          <TableRow>
            <TableCell colSpan={4}>
              <Alert variant="destructive">
                <AlertDescription>{error.description}</AlertDescription>
              </Alert>
            </TableCell>
          </TableRow>
        )}

        {!isLoading && !error && isEmpty && (
          <TableRow>
            <TableCell colSpan={4} className="text-center text-muted-foreground">
              No workflows yet. Create your first workflow to get started.
            </TableCell>
          </TableRow>
        )}

        {!isLoading &&
          !error &&
          workflows.map((workflow) => (
            <TableRow key={workflow.id}>
              <TableCell>
                <Link
                  to={`/workflows/${workflow.id}`}
                  className="font-medium text-foreground underline-offset-4 hover:underline"
                >
                  {workflow.name}
                </Link>
              </TableCell>
              <TableCell>
                <WorkflowStatusBadge state={workflow.state} />
              </TableCell>
              <TableCell>{formatDate(workflow.created_at)}</TableCell>
              <TableCell>{formatDate(workflow.updated_at)}</TableCell>
            </TableRow>
          ))}
      </TableBody>
    </Table>
  )
}

export function WorkflowTableLoadingCaption() {
  return (
    <p className="inline-flex items-center gap-2 text-sm text-muted-foreground" role="status">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      Loading workflows...
    </p>
  )
}
