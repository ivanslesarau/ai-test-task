import { z } from 'zod'

/** Mirrors `ApprovalDecisionRequest` (contracts/frontend-contracts.md
 * §17) — the body `approve` and `deny` carry. `note` is optional; an
 * opened-but-empty note box normalizes to `null` via
 * `normalizeEmptyToNull`, never `''` (constitution Principle VI). */
export const approvalDecisionSchema = z.object({
  note: z.string().max(1000),
})

export type ApprovalDecisionValues = z.infer<typeof approvalDecisionSchema>

/** Mirrors `ApprovalInfoRequest` — the body `request-info` and
 * `respond` carry. `note` is REQUIRED here: asking for more information
 * without saying what is wanted, or replying without saying anything,
 * is not a message (FR-150, FR-153). */
export const approvalInfoSchema = z.object({
  note: z.string().trim().min(1, 'Say what you need before sending.').max(1000),
})

export type ApprovalInfoValues = z.infer<typeof approvalInfoSchema>
