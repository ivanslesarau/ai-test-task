import { useMutation, useQuery } from '@tanstack/react-query'

import { apiClient } from '@/shared/api/client'

interface InvitationCheck {
  email_hint: string
  expires_at: string
}

export function useInvitationCheck(token: string) {
  return useQuery({
    queryKey: ['invitation-check', token],
    queryFn: async (): Promise<InvitationCheck> => {
      const { data } = await apiClient.get<InvitationCheck>(`/auth/setup-password/${token}`)
      return data
    },
    retry: false,
  })
}

export function useSetupPassword() {
  return useMutation({
    mutationFn: async (values: { token: string; password: string }): Promise<void> => {
      await apiClient.post('/auth/setup-password', values)
    },
  })
}
