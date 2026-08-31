import type { CoachInvitationPresentedState } from '@/shared/api/types'

/** `GET /trainer/coach-invitations`' own query parameters — page, page
 * size, and the optional presented-state filter (contracts/openapi.yaml).
 */
export interface CoachInvitationListParams {
  page: number
  page_size: number
  state?: CoachInvitationPresentedState
}

/**
 * Single source of truth for every coach-invitation query key
 * (contracts/frontend-contracts.md §31). `preview` is declared here even
 * though User Story 1 never calls it — it belongs to the same resource
 * `GET /coach-invitations/{token}` will read once User Story 2 (tasks.md
 * T559) adds the hook that uses it, and the contract defines all three
 * keys as one factory rather than splitting it across two stories' files.
 */
export const coachInvitationKeys = {
  all: ['coach-invitations'] as const,
  list: (params: CoachInvitationListParams) => ['coach-invitations', 'list', params] as const,
  preview: (token: string) => ['coach-invitations', 'preview', token] as const,
}
