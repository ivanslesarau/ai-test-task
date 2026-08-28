import { useMutation, useQueryClient } from '@tanstack/react-query'

import { familyKeys } from '@/entities/player-profile/api/query-keys'
import { ctxKeys } from '@/entities/trainer-context/api/query-keys'
import { sessionKey } from '@/entities/session/api/use-session'
import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { JoinAcceptRequest, JoinResult } from '@/shared/api/types'

export function useAcceptJoinLink(code: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body?: JoinAcceptRequest): Promise<JoinResult> => {
      const { data } = await apiClient.post<JoinResult>(`/join/${code}/accept`, body)
      return data
    },
    onSuccess: () => {
      // A genuinely new join changes both the session's active context
      // and the switcher's list, and — per R-26/R-47 — every
      // context-scoped response cached under the old context must be
      // discarded before the new one renders. A family-member selection
      // (Story 13) may also add profiles the family list has never
      // shown associated before (contracts/frontend-contracts.md §16).
      void queryClient.invalidateQueries({ queryKey: sessionKey })
      void queryClient.invalidateQueries({ queryKey: userKeys.contexts })
      void queryClient.invalidateQueries({ queryKey: familyKeys.profiles })
      queryClient.removeQueries({ queryKey: ctxKeys.root })
    },
  })
}
