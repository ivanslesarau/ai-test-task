import type { RosterSearch } from '@/entities/trainer-context/model/roster-search'

/**
 * THE context namespace (contracts/frontend-contracts.md §9, research.md
 * R-26). Every query for data belonging to one trainer goes under
 * `['ctx', trainerId, ...]` — the roster today, and every calendar, token
 * balance, reservation, and content list Epics 02-08 add. A component
 * asking under the new trainer's namespace cannot be served the previous
 * trainer's cached response, because that response is filed under a
 * different key.
 *
 * A trainer's *own* keys (userKeys.shareLink, userKeys.branding) stay
 * outside this namespace: a trainer is not in a switchable context.
 */
export const ctxKeys = {
  root: ['ctx'] as const,
  scope: (trainerId: string) => ['ctx', trainerId] as const,
  players: (trainerId: string, search: RosterSearch) =>
    ['ctx', trainerId, 'players', search] as const,
} as const
