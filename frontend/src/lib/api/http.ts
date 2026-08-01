import type { AxiosRequestConfig } from "axios"
import { client } from "./client"

export function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return client.get<T>(url, config).then((r) => r.data)
}

export function post<T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<T> {
  return client.post<T>(url, body, config).then((r) => r.data)
}

export function put<T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig
): Promise<T> {
  return client.put<T>(url, body, config).then((r) => r.data)
}

export function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return client.delete<T>(url, config).then((r) => r.data)
}
