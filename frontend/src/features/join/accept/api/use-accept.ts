import { useMutation, useQueryClient } from '@tanstack/react-query'

import { sessionKey } from '@/entities/session/api/use-session'
import { userKeys } from '@/entities/user/api/query-keys'
import { ctxKeys } from '@/entities/trainer-context/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { JoinResult } from '@/shared/api/types'

export function useAcceptJoinLink(code: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (): Promise<JoinResult> => {
      const { data } = await apiClient.post<JoinResult>(`/join/${code}/accept`)
      return data
    },
    onSuccess: () => {
      // A genuinely new join changes both the session's active context
      // and the switcher's list, and — per R-26 — every context-scoped
      // response cached under the old context must be discarded before
      // the new one renders.
      void queryClient.invalidateQueries({ queryKey: sessionKey })
      void queryClient.invalidateQueries({ queryKey: userKeys.trainers })
      queryClient.removeQueries({ queryKey: ctxKeys.root })
    },
  })
}
