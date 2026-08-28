import { z } from 'zod'

/** Mirrors the backend's `PlayerProfileUpdate` (contracts/openapi.yaml,
 * contracts/frontend-contracts.md §17). Every field optional at the
 * schema level; which of them the form actually renders and submits is
 * driven by the profile's `kind` — name fields for a `child` only,
 * `tokens_without_approval` for the owning parent only — never by this
 * schema alone. */
export const playerProfileUpdateSchema = z.object({
  first_name: z.string().min(1, 'First name is required').max(100).optional(),
  last_name: z.string().min(1, 'Last name is required').max(100).optional(),
  date_of_birth: z.string().min(1, 'Date of birth is required').optional(),
  gender: z.enum(['male', 'female', 'other', 'prefer_not_to_say']).optional(),
  school: z.string().max(200).optional(),
  jersey_number: z.string().max(10).optional(),
  tokens_without_approval: z.boolean().optional(),
})

export type PlayerProfileUpdateValues = z.infer<typeof playerProfileUpdateSchema>
