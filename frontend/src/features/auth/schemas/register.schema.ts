import { z } from "zod"

export const registerSchema = z.object({
  username: z.string().min(1, "Username is required."),
  email: z.string().min(1, "Email is required.").email("Enter a valid email."),
  password: z.string().min(8, "Password must be at least 8 characters."),
})

export type RegisterSchema = z.infer<typeof registerSchema>
