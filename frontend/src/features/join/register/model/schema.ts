import { z } from 'zod'

function ageOn(dobIso: string, today: Date): number {
  const dob = new Date(`${dobIso}T00:00:00`)
  let age = today.getFullYear() - dob.getFullYear()
  const monthDiff = today.getMonth() - dob.getMonth()
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
    age -= 1
  }
  return age
}

/** Mirrors the backend's JoinRegistrationRequest (contracts/openapi.yaml,
 * schemas/join.py). The age-band refinement matches the backend's
 * `_age_matches_is_self` model_validator exactly: self ⇒ 18 or older,
 * dependant ⇒ 1 to 18 (FR-077). Attached to `date_of_birth` so the
 * message renders beside the field the person can act on. */
export const joinRegistrationSchema = z
  .object({
    first_name: z.string().min(1, 'First name is required').max(100),
    last_name: z.string().min(1, 'Last name is required').max(100),
    email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
    password: z.string().min(12, 'Password must be at least 12 characters').max(128),
    phone: z.string().min(1, 'Phone number is required').max(32),
    is_self: z.boolean(),
    player_name: z.string().max(200),
    date_of_birth: z.string().min(1, 'Date of birth is required'),
    gender: z.enum(['male', 'female', 'other', 'prefer_not_to_say']),
  })
  .superRefine((values, ctx) => {
    if (!values.is_self && !values.player_name.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['player_name'],
        message: 'Enter the name of the player you are registering.',
      })
    }
    if (!values.date_of_birth) return
    const age = ageOn(values.date_of_birth, new Date())
    if (values.is_self && age < 18) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['date_of_birth'],
        message: 'You must be 18 or older to register yourself as the player.',
      })
    }
    if (!values.is_self && (age < 1 || age > 18)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['date_of_birth'],
        message: "A dependant player's age must be between 1 and 18.",
      })
    }
  })

export type JoinRegistrationValues = z.infer<typeof joinRegistrationSchema>
