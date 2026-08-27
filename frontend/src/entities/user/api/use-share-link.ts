import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { ShareLink } from '@/shared/api/types'

export function useOwnShareLink() {
  return useQuery({
    queryKey: userKeys.shareLink,
    queryFn: async (): Promise<ShareLink> => {
      const { data } = await apiClient.get<ShareLink>('/me/share-link')
      return data
    },
  })
}

export function useRegenerateShareLink() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (): Promise<ShareLink> => {
      const { data } = await apiClient.post<ShareLink>('/me/share-link/regenerate')
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.shareLink })
    },
  })
}
