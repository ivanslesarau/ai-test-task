import { isApiError } from '@/shared/api/errors'
import type { CoachInvitation } from '@/shared/api/types'

/** Narrows a failed `issueCoachInvitation` mutation's error down to the
 * existing invitation a 409 `coach_invitation_pending` response carries
 * (contracts/openapi.yaml `CoachInvitationConflict`, FR-007). Reads from
 * the mutation's own error state, never a store (contracts/frontend-
 * contracts.md §18), mirroring `add-child`'s `getDuplicateMatches`. */
export function getPendingInvitation(error: unknown): CoachInvitation | null {
  if (!isApiError(error) || error.code !== 'coach_invitation_pending') return null
  const invitation = error.raw.invitation
  return invitation && typeof invitation === 'object' ? (invitation as CoachInvitation) : null
}
