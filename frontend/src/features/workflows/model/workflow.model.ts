// Canonical set of states that mark a workflow as no longer progressing.
export const TERMINAL_STATES = new Set(["SUCCESS", "FAILED"])

export function isTerminal(state: string): boolean {
  return TERMINAL_STATES.has(state.trim().toUpperCase())
}
