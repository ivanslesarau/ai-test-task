/** `GET /trainer/coaches`' own query parameters (contracts/openapi.yaml). */
export interface CoachRosterParams {
  page: number
  page_size: number
  q?: string
}

/**
 * Single source of truth for every coach-roster query key
 * (contracts/frontend-contracts.md §31).
 */
export const coachKeys = {
  all: ['coaches'] as const,
  roster: (params: CoachRosterParams) => ['coaches', 'roster', params] as const,
  detail: (coachUserId: string) => ['coaches', 'detail', coachUserId] as const,
}
