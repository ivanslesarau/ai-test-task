import { useMutation, useQueryClient } from '@tanstack/react-query'

import { sessionKey } from '@/entities/session/api/use-session'
import { apiClient } from '@/shared/api/client'
import type { CoachJoinResult } from '@/shared/api/types'

/** `POST /coach-invitations/{token}/accept` (FR-012 – FR-019, FR-023) —
 * for an already signed-in coach. A fresh join and FR-016's no-op both
 * change the caller's trainer and branding, so the session is
 * invalidated either way. */
export function useAcceptCoachInvitation(token: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (): Promise<CoachJoinResult> => {
      const { data } = await apiClient.post<CoachJoinResult>(
        `/coach-invitations/${token}/accept`,
      )
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKey })
    },
  })
}
