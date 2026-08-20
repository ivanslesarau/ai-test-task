import { z } from 'zod'

/** Mirrors the backend's CreateUserRequest (contracts/openapi.yaml). */
export const createUserSchema = z
  .object({
    role: z.enum(['super_admin', 'trainer', 'coach', 'player_parent']),
    email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
    first_name: z.string().min(1, 'First name is required').max(100),
    last_name: z.string().min(1, 'Last name is required').max(100),
    phone: z.string().min(1, 'Phone number is required').max(32),
    business_name: z.string().max(200),
  })
  .superRefine((values, ctx) => {
    if (values.role === 'trainer' && !values.business_name?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['business_name'],
        message: 'Business name is required for a Trainer account',
      })
    }
  })

export type CreateUserValues = z.infer<typeof createUserSchema>
