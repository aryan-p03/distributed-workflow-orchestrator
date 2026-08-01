import { get, post } from "@/lib/api/http"
import type { LoginRequest, RegisterRequest, UserResponse } from "../types/auth.types"

export function login(body: LoginRequest): Promise<UserResponse> {
  return post<UserResponse, LoginRequest>("/auth/login", body).then(() => me())
}

export function register(body: RegisterRequest): Promise<UserResponse> {
  return post<UserResponse, RegisterRequest>("/auth/register", body)
}

export function logout(): Promise<void> {
  return post<void>("/auth/logout")
}

export function me(): Promise<UserResponse> {
  return get<UserResponse>("/auth/me")
}
