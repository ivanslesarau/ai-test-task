import { useMutation, useQueryClient } from '@tanstack/react-query'

import { sessionKey } from '@/entities/session/api/use-session'
import { apiClient } from '@/shared/api/client'
import type { CoachJoinResult, CoachRegistrationRequest } from '@/shared/api/types'

/** `POST /coach-invitations/{token}/register` (FR-011, FR-013, FR-017,
 * FR-018, FR-023). The response sets the session cookie — refetching the
 * session, rather than constructing a `CurrentUser` from the result,
 * keeps one source of truth for what "signed in" means (role, trainer,
 * and branding all changed, frontend-contracts.md §31). */
export function useRegisterThroughCoachInvitation(token: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: CoachRegistrationRequest): Promise<CoachJoinResult> => {
      const { data } = await apiClient.post<CoachJoinResult>(
        `/coach-invitations/${token}/register`,
        body,
      )
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKey })
    },
  })
}
