import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useNavigate } from "react-router-dom"
import { register as apiRegister, login as apiLogin } from "../api/auth.api"
import { registerSchema, type RegisterSchema } from "../schemas/register.schema"
import { useAuth } from "./use-auth"
import type { APIError } from "@/lib/api/errors"

export function useRegister() {
  const { refresh } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)

  const form = useForm<RegisterSchema>({
    resolver: zodResolver(registerSchema),
    defaultValues: { username: "", email: "", password: "" },
  })

  async function onSubmit(data: RegisterSchema) {
    setServerError(null)
    try {
      await apiRegister(data)
      await apiLogin({ email: data.email, password: data.password })
      await refresh()
      navigate("/")
    } catch (err) {
      const apiErr = err as APIError
      if (apiErr.source?.type === "field") {
        form.setError(apiErr.source.name as keyof RegisterSchema, {
          message: apiErr.description,
        })
      } else {
        setServerError(apiErr.description ?? "Registration failed.")
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
