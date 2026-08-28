import { isApiError } from '@/shared/api/errors'
import type { PlayerProfile } from '@/shared/api/types'

/** Narrows a failed `createChildProfile` mutation's error down to the
 * matched profiles a 409 `possible_duplicate_profile` response carries
 * (contracts/openapi.yaml `DuplicateProfileError`, research.md R-45).
 * Reads from the mutation's own error state, never a store
 * (contracts/frontend-contracts.md §18). */
export function getDuplicateMatches(error: unknown): PlayerProfile[] | null {
  if (!isApiError(error) || error.code !== 'possible_duplicate_profile') return null
  const matches = error.raw.matches
  return Array.isArray(matches) ? (matches as PlayerProfile[]) : null
}
