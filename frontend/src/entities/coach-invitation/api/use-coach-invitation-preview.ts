import { useQuery } from '@tanstack/react-query'

import { coachInvitationKeys } from '@/entities/coach-invitation/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { CoachInvitationPreview } from '@/shared/api/types'

/** `GET /coach-invitations/{token}` (FR-011 – FR-013) — public and
 * unauthenticated. Every unusable token renders the same single refusal
 * (`retry: false`, since a 404 here is never transient). */
export function useCoachInvitationPreview(token: string) {
  return useQuery({
    queryKey: coachInvitationKeys.preview(token),
    queryFn: async (): Promise<CoachInvitationPreview> => {
      const { data } = await apiClient.get<CoachInvitationPreview>(`/coach-invitations/${token}`)
      return data
    },
    retry: false,
  })
}
