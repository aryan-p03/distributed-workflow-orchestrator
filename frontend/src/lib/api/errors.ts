import type { AxiosError } from "axios"

export interface APIErrorSource {
  type: "field" | "header" | "parameter"
  name: string
}

export interface APIError {
  code: string
  description: string
  source?: APIErrorSource
}

interface BackendErrorDetail {
  code?: string
  description?: string
  msg?: string
  loc?: (string | number)[]
  type?: string
}

interface BackendErrorBody {
  detail?: string | BackendErrorDetail | BackendErrorDetail[]
}

export function toAPIError(error: unknown): APIError {
  const axiosErr = error as AxiosError<BackendErrorBody>
  if (!axiosErr.isAxiosError) {
    return { code: "UNKNOWN", description: "An unexpected error occurred." }
  }

  const data = axiosErr.response?.data
  const status = axiosErr.response?.status

  if (!data) {
    if (status === 401) return { code: "UNAUTHORIZED", description: "Authentication required." }
    if (status === 403) return { code: "FORBIDDEN", description: "Access denied." }
    return { code: "NETWORK_ERROR", description: "Network error. Please try again." }
  }

  const detail = data.detail

  // FastAPI validation error array
  if (Array.isArray(detail)) {
    const first = detail[0]
    const fieldName =
      first.loc && first.loc.length > 1 ? String(first.loc[first.loc.length - 1]) : undefined
    return {
      code: first.code ?? first.type ?? "VALIDATION_ERROR",
      description: first.description ?? first.msg ?? "Validation error.",
      source: fieldName ? { type: "field", name: fieldName } : undefined,
    }
  }

  if (typeof detail === "object" && detail !== null) {
    return {
      code: detail.code ?? "API_ERROR",
      description: detail.description ?? detail.msg ?? "An error occurred.",
    }
  }

  if (typeof detail === "string") {
    return { code: "API_ERROR", description: detail }
  }

  return { code: "UNKNOWN", description: "An unexpected error occurred." }
}
