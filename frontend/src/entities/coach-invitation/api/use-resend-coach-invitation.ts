import { useMutation, useQueryClient } from '@tanstack/react-query'

import { coachInvitationKeys } from '@/entities/coach-invitation/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { CoachInvitation } from '@/shared/api/types'

/** `POST /trainer/coach-invitations/{invitation_id}/resend` (FR-005) — the
 * old link stops working and the response is the replacement invitation. */
export function useResendCoachInvitation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (invitationId: string): Promise<CoachInvitation> => {
      const { data } = await apiClient.post<CoachInvitation>(
        `/trainer/coach-invitations/${invitationId}/resend`,
      )
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: coachInvitationKeys.all })
    },
  })
}
