import { afterEach, describe, expect, it, vi } from "vitest"

async function loadClient() {
  vi.resetModules()
  return import("./client")
}

afterEach(() => {
  vi.unstubAllEnvs()
})

describe("API client configuration", () => {
  it("uses the configured VITE_API_BASE_URL", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.example.test")

    const { client } = await loadClient()

    expect(client.defaults.baseURL).toBe("http://api.example.test")
  })

  it("falls back to the local API URL", async () => {
    const { client } = await loadClient()

    expect(client.defaults.baseURL).toBe("http://localhost:8000")
  })
})
