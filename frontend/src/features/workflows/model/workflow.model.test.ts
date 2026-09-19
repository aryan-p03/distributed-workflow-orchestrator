import { describe, expect, it } from "vitest"
import { isTerminal, TERMINAL_STATES } from "./workflow.model"

describe("workflow.model", () => {
  describe("TERMINAL_STATES", () => {
    it("contains SUCCESS and FAILED", () => {
      expect(TERMINAL_STATES.has("SUCCESS")).toBe(true)
      expect(TERMINAL_STATES.has("FAILED")).toBe(true)
    })

    it("does not contain active states", () => {
      expect(TERMINAL_STATES.has("RUNNING")).toBe(false)
      expect(TERMINAL_STATES.has("QUEUED")).toBe(false)
      expect(TERMINAL_STATES.has("CREATED")).toBe(false)
    })
  })

  describe("isTerminal", () => {
    it("returns true for success state (case-insensitive)", () => {
      expect(isTerminal("success")).toBe(true)
      expect(isTerminal("SUCCESS")).toBe(true)
    })

    it("returns true for failed state", () => {
      expect(isTerminal("failed")).toBe(true)
      expect(isTerminal("FAILED")).toBe(true)
    })

    it("returns false for active states", () => {
      expect(isTerminal("running")).toBe(false)
      expect(isTerminal("queued")).toBe(false)
      expect(isTerminal("created")).toBe(false)
    })

    it("handles surrounding whitespace", () => {
      expect(isTerminal("  SUCCESS  ")).toBe(true)
    })
  })
})
