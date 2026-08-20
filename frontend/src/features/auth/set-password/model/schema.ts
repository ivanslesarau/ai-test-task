import { z } from 'zod'

export const setPasswordSchema = z
  .object({
    password: z.string().min(12, 'Password must be at least 12 characters').max(128),
    confirmPassword: z.string().min(1, 'Confirm your password'),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

export type SetPasswordValues = z.infer<typeof setPasswordSchema>
