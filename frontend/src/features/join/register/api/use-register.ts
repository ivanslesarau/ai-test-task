import { useMutation, useQueryClient } from '@tanstack/react-query'

import { sessionKey } from '@/entities/session/api/use-session'
import { apiClient } from '@/shared/api/client'
import type { JoinRegistrationRequest, JoinResult } from '@/shared/api/types'

export function useRegisterThroughJoinLink(code: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: JoinRegistrationRequest): Promise<JoinResult> => {
      const { data } = await apiClient.post<JoinResult>(`/join/${code}/register`, body)
      return data
    },
    onSuccess: () => {
      // The response set the session cookie (FR-078) — refetching the
      // session, rather than constructing a CurrentUser from JoinResult,
      // keeps one source of truth for what "signed in" means.
      void queryClient.invalidateQueries({ queryKey: sessionKey })
    },
  })
}
