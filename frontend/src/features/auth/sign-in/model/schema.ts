import { z } from 'zod'

/** Mirrors the backend's LoginRequest (contracts/openapi.yaml). */
export const signInSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})

export type SignInValues = z.infer<typeof signInSchema>
