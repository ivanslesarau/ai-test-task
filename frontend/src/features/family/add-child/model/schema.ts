import { z } from 'zod'

/** The same derivation the backend uses (research.md R-31) — never stored,
 * recomputed from `date_of_birth` at the moment it matters. */
function ageOn(dateOfBirth: string, today: Date): number {
  const dob = new Date(dateOfBirth)
  let years = today.getFullYear() - dob.getFullYear()
  const todayMonth = today.getMonth()
  const todayDate = today.getDate()
  const dobMonth = dob.getMonth()
  const dobDate = dob.getDate()
  if (todayMonth < dobMonth || (todayMonth === dobMonth && todayDate < dobDate)) {
    years -= 1
  }
  return years
}

/** Mirrors the backend's `CreateChildProfileRequest`
 * (contracts/openapi.yaml, contracts/frontend-contracts.md §17). */
export const createChildProfileSchema = z
  .object({
    first_name: z.string().min(1, 'First name is required').max(100),
    last_name: z.string().min(1, 'Last name is required').max(100),
    date_of_birth: z.string().min(1, 'Date of birth is required'),
    gender: z.enum(['male', 'female', 'other', 'prefer_not_to_say'], {
      message: 'Select a gender',
    }),
    school: z.string().max(200),
    jersey_number: z.string().max(10),
    // Every trainer_ids entry the account already trains with; may be
    // empty (FR-123). The exact set offered is validated server-side —
    // this schema only shapes the payload.
    trainer_ids: z.array(z.string()),
    acknowledge_possible_duplicate: z.boolean(),
  })
  .superRefine((values, ctx) => {
    if (values.date_of_birth.trim() === '') return
    const dob = new Date(values.date_of_birth)
    if (Number.isNaN(dob.getTime()) || dob.getTime() > Date.now()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['date_of_birth'],
        message: 'Enter a real past date',
      })
      return
    }
    const age = ageOn(values.date_of_birth, new Date())
    if (age < 1 || age > 18) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['date_of_birth'],
        message: "A child's age must be between 1 and 18",
      })
    }
  })

export type CreateChildProfileValues = z.infer<typeof createChildProfileSchema>
