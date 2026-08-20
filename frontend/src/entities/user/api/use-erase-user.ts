import { useMutation, useQueryClient } from '@tanstack/react-query'

import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { EraseUserRequest, UserDetail } from '@/shared/api/types'

interface EraseVariables extends EraseUserRequest {
  userId: string
}

export function useEraseUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ userId, ...body }: EraseVariables): Promise<UserDetail> => {
      const { data } = await apiClient.post<UserDetail>(`/admin/users/${userId}/erase`, body)
      return data
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: userKeys.detail(variables.userId) })
      void queryClient.invalidateQueries({ queryKey: userKeys.all })
      void queryClient.invalidateQueries({ queryKey: userKeys.erasureRecord(variables.userId) })
    },
  })
}
