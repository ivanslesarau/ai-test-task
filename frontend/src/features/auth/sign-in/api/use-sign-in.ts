import { useMutation, useQueryClient } from '@tanstack/react-query'

import { sessionKey } from '@/entities/session/api/use-session'
import { apiClient } from '@/shared/api/client'
import type { CurrentUser, LoginRequest } from '@/shared/api/types'

export function useSignIn() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (values: LoginRequest): Promise<CurrentUser> => {
      const { data } = await apiClient.post<CurrentUser>('/auth/login', values)
      return data
    },
    onSuccess: (user) => {
      queryClient.setQueryData(sessionKey, user)
    },
  })
}
