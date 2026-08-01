import { describe, it, expect } from "vitest"
import { toAPIError } from "@/lib/api/errors"

function makeAxiosError(status: number, data: unknown) {
  return Object.assign(new Error("AxiosError"), {
    isAxiosError: true,
    response: { status, data },
    config: { url: "/some-endpoint" },
  })
}

describe("toAPIError", () => {
  it("converts 401 with no data to UNAUTHORIZED", () => {
    const err = Object.assign(new Error(), {
      isAxiosError: true,
      response: { status: 401, data: null },
      config: { url: "/workflows" },
    })
    expect(toAPIError(err)).toEqual({
      code: "UNAUTHORIZED",
      description: "Authentication required.",
    })
  })

  it("converts string detail to API_ERROR", () => {
    const err = makeAxiosError(409, { detail: "Username already taken." })
    expect(toAPIError(err)).toEqual({ code: "API_ERROR", description: "Username already taken." })
  })

  it("converts FastAPI validation error array to first field error", () => {
    const err = makeAxiosError(422, {
      detail: [{ loc: ["body", "email"], msg: "Invalid email.", type: "value_error" }],
    })
    const result = toAPIError(err)
    expect(result.code).toBe("value_error")
    expect(result.description).toBe("Invalid email.")
    expect(result.source).toEqual({ type: "field", name: "email" })
  })

  it("converts non-axios error to UNKNOWN", () => {
    expect(toAPIError(new Error("boom"))).toEqual({
      code: "UNKNOWN",
      description: "An unexpected error occurred.",
    })
  })
})
