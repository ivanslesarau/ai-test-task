import { useMutation, useQueryClient } from '@tanstack/react-query'

import { coachInvitationKeys } from '@/entities/coach-invitation/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { CoachInvitation, CoachInvitationCreate } from '@/shared/api/types'

/** `POST /trainer/coach-invitations` (FR-001 – FR-003, FR-007, FR-008,
 * FR-010). The response is identical in shape and status whether or not
 * the address already holds an account — this hook has no branch on that,
 * because the server never tells it either. */
export function useIssueCoachInvitation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: CoachInvitationCreate): Promise<CoachInvitation> => {
      const { data } = await apiClient.post<CoachInvitation>('/trainer/coach-invitations', body)
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: coachInvitationKeys.all })
    },
  })
}
