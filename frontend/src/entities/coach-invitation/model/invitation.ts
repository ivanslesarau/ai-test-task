import { z } from 'zod'

import type { CoachInvitationPresentedState } from '@/shared/api/types'

/**
 * Mirrors `CoachInvitationCreate` (contracts/openapi.yaml,
 * contracts/frontend-contracts.md §32). `invitee_name`/`message` are typed
 * as plain (non-nullable) `string` here because a controlled input yields
 * `''` — the shared normalizer in `shared/lib/normalize-payload.ts` turns
 * `''` into `null` before the payload reaches axios (Principle VI). No
 * inline ternary belongs at a form's call site.
 */
export const coachInvitationCreateSchema = z.object({
  email: z.string().email().max(320),
  invitee_name: z.string().max(200),
  message: z.string().max(2000),
})

export type CoachInvitationCreateValues = z.infer<typeof coachInvitationCreateSchema>

/** The one label per presented state (data-model.md §101.1) — the client
 * never recomputes the precedence, only renders what the server already
 * derived. */
export const COACH_INVITATION_STATE_LABELS: Record<CoachInvitationPresentedState, string> = {
  awaiting: 'Awaiting response',
  accepted: 'Accepted',
  expired: 'Expired',
  revoked: 'Revoked',
  blocked: 'Blocked',
}
