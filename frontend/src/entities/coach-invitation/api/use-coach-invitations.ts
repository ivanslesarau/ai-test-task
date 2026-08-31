import { keepPreviousData, useQuery } from '@tanstack/react-query'

import type { CoachInvitationListParams } from '@/entities/coach-invitation/api/query-keys'
import { coachInvitationKeys } from '@/entities/coach-invitation/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { CoachInvitationPage } from '@/shared/api/types'

/** `GET /trainer/coach-invitations` (FR-004, FR-009) — the trainer's own
 * invitations, newest first. `superseded` rows are never in the response
 * at all (FR-005). */
export function useCoachInvitations(params: CoachInvitationListParams) {
  return useQuery({
    queryKey: coachInvitationKeys.list(params),
    queryFn: async (): Promise<CoachInvitationPage> => {
      const { data } = await apiClient.get<CoachInvitationPage>('/trainer/coach-invitations', {
        params,
      })
      return data
    },
    placeholderData: keepPreviousData,
  })
}
