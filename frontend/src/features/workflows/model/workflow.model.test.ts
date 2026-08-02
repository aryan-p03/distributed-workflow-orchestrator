import { describe, expect, it } from "vitest"
import { isTerminal, TERMINAL_STATES } from "./workflow.model"

describe("workflow.model", () => {
  describe("TERMINAL_STATES", () => {
    it("contains COMPLETED, FAILED, and CANCELLED", () => {
      expect(TERMINAL_STATES.has("COMPLETED")).toBe(true)
      expect(TERMINAL_STATES.has("FAILED")).toBe(true)
      expect(TERMINAL_STATES.has("CANCELLED")).toBe(true)
    })

    it("does not contain active states", () => {
      expect(TERMINAL_STATES.has("RUNNING")).toBe(false)
      expect(TERMINAL_STATES.has("QUEUED")).toBe(false)
      expect(TERMINAL_STATES.has("CREATED")).toBe(false)
    })
  })

  describe("isTerminal", () => {
    it("returns true for completed state (case-insensitive)", () => {
      expect(isTerminal("completed")).toBe(true)
      expect(isTerminal("COMPLETED")).toBe(true)
      expect(isTerminal("success")).toBe(false)
    })

    it("returns true for failed state", () => {
      expect(isTerminal("failed")).toBe(true)
      expect(isTerminal("FAILED")).toBe(true)
    })

    it("returns true for cancelled state", () => {
      expect(isTerminal("cancelled")).toBe(true)
      expect(isTerminal("CANCELLED")).toBe(true)
    })

    it("returns false for active states", () => {
      expect(isTerminal("running")).toBe(false)
      expect(isTerminal("queued")).toBe(false)
      expect(isTerminal("created")).toBe(false)
    })

    it("handles surrounding whitespace", () => {
      expect(isTerminal("  COMPLETED  ")).toBe(true)
    })
  })
})
