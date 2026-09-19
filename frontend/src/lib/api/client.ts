import axios from "axios"
import { toAPIError } from "./errors"

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  withCredentials: true,
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status
    const requestUrl: string = error?.config?.url ?? ""
    const isAuthPath = requestUrl.startsWith("/auth")

    if (status === 401 && !isAuthPath) {
      window.location.href = "/login"
    }

    return Promise.reject(toAPIError(error))
  }
)
