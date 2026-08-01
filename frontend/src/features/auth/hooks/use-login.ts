import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useNavigate } from "react-router-dom"
import { login as apiLogin } from "../api/auth.api"
import { loginSchema, type LoginSchema } from "../schemas/login.schema"
import { useAuth } from "./use-auth"
import type { APIError } from "@/lib/api/errors"

export function useLogin() {
  const { refresh } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)

  const form = useForm<LoginSchema>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  })

  async function onSubmit(data: LoginSchema) {
    setServerError(null)
    try {
      await apiLogin(data)
      await refresh()
      navigate("/")
    } catch (err) {
      const apiErr = err as APIError
      if (apiErr.source?.type === "field") {
        form.setError(apiErr.source.name as keyof LoginSchema, {
          message: apiErr.description,
        })
      } else {
        setServerError(apiErr.description ?? "Login failed.")
      }
    }
  }

  return {
    form,
    onSubmit: form.handleSubmit(onSubmit),
    serverError,
    isSubmitting: form.formState.isSubmitting,
  }
}
