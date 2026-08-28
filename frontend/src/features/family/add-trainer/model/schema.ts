import { z } from 'zod'

/** Mirrors `AddPlayerTrainerRequest` (contracts/openapi.yaml,
 * contracts/frontend-contracts.md §17). Exactly one of `code` or
 * `trainer_id` — a `.refine` on the object, not on either field, because
 * the rule is about the pair. */
export const addPlayerTrainerSchema = z
  .object({
    code: z.string().max(64),
    trainer_id: z.string(),
  })
  .superRefine((values, ctx) => {
    const hasCode = values.code.trim().length >= 8
    const hasTrainerId = values.trainer_id.trim().length > 0
    if (hasCode === hasTrainerId) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        // Attached to the object root, not either field — the rule is
        // about the pair (contracts/frontend-contracts.md §17) — and
        // additionally mirrored onto `code` so it renders inline the same
        // way every other field error does, rather than only as the
        // form-level message.
        message: 'Enter an invitation code, or choose a trainer — not both, and not neither',
      })
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['code'],
        message: 'Enter an invitation code, or choose a trainer — not both, and not neither',
      })
    }
  })

export type AddPlayerTrainerValues = z.infer<typeof addPlayerTrainerSchema>
