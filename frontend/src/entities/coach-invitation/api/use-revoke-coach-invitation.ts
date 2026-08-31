import { useMutation, useQueryClient } from '@tanstack/react-query'

import { coachInvitationKeys } from '@/entities/coach-invitation/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { CoachInvitation } from '@/shared/api/types'

/** `POST /trainer/coach-invitations/{invitation_id}/revoke` (FR-006) —
 * the invitation, now revoked. */
export function useRevokeCoachInvitation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (invitationId: string): Promise<CoachInvitation> => {
      const { data } = await apiClient.post<CoachInvitation>(
        `/trainer/coach-invitations/${invitationId}/revoke`,
      )
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: coachInvitationKeys.all })
    },
  })
}
