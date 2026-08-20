import { useMutation, useQueryClient } from '@tanstack/react-query'

import { apiClient } from '@/shared/api/client'

export function useSignOut() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/auth/logout')
    },
    onSuccess: () => {
      queryClient.clear()
    },
  })
}
