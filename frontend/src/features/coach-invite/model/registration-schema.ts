import { z } from 'zod'

/**
 * Mirrors `CoachRegistrationRequest` (contracts/openapi.yaml,
 * schemas/coach.py). No `email`, `role`, or `trainer_id` field — all
 * three come from the invitation (FR-011, FR-013). `phone`/`bio`/
 * `credentials`/`certifications` are typed as plain (non-nullable)
 * `string` here because a controlled input yields `''`; the shared
 * normalizer in `shared/lib/normalize-payload.ts` turns `''` into `null`
 * before the payload reaches axios (Principle VI).
 */
export const coachRegistrationSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100),
  last_name: z.string().min(1, 'Last name is required').max(100),
  password: z.string().min(12, 'Password must be at least 12 characters').max(128),
  phone: z.string().max(32),
  bio: z.string().max(2000),
  credentials: z.string().max(1000),
  certifications: z.string().max(1000),
})

export type CoachRegistrationValues = z.infer<typeof coachRegistrationSchema>
