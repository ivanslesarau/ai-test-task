import { useMutation, useQueryClient } from '@tanstack/react-query'

import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { StatusChangeRequest, UserDetail } from '@/shared/api/types'

interface StatusChangeVariables extends StatusChangeRequest {
  userId: string
}

/**
 * `userId` travels as part of the mutation's variables, not as a
 * parameter closed over when the hook is called. A hook-level parameter
 * would bind the mutationFn to whatever id was current on the render
 * that first called the hook; since these dialogs mount as soon as a
 * pendingAction appears (the same render that supplies the id), passing
 * it through variables instead removes any dependency on which render's
 * closure ends up wired to the button's event handler.
 */
export function useDeactivateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ userId, ...body }: StatusChangeVariables): Promise<UserDetail> => {
      const { data } = await apiClient.post<UserDetail>(
        `/admin/users/${userId}/deactivate`,
        body,
      )
      return data
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: userKeys.detail(variables.userId) })
      void queryClient.invalidateQueries({ queryKey: userKeys.all })
    },
  })
}

export function useReactivateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ userId, ...body }: StatusChangeVariables): Promise<UserDetail> => {
      const { data } = await apiClient.post<UserDetail>(
        `/admin/users/${userId}/reactivate`,
        body,
      )
      return data
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: userKeys.detail(variables.userId) })
      void queryClient.invalidateQueries({ queryKey: userKeys.all })
    },
  })
}
