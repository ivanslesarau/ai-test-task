import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { sessionKey } from '@/entities/session/api/use-session'
import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { PortalBranding, PortalBrandingUpdate } from '@/shared/api/types'

export function useOwnBranding() {
  return useQuery({
    queryKey: userKeys.branding,
    queryFn: async (): Promise<PortalBranding> => {
      const { data } = await apiClient.get<PortalBranding>('/me/branding')
      return data
    },
  })
}

function useInvalidateBrandingAndSession() {
  const queryClient = useQueryClient()
  return () => {
    // A saved branding change must reach every signed-in player and
    // coach on their next view without them signing out (FR-102,
    // SC-022) — invalidating `session` is what makes that true, since
    // `portal_branding` on CurrentUser is what the app shell paints from.
    void queryClient.invalidateQueries({ queryKey: userKeys.branding })
    void queryClient.invalidateQueries({ queryKey: sessionKey })
  }
}

export function useUpdateBranding() {
  const invalidate = useInvalidateBrandingAndSession()

  return useMutation({
    mutationFn: async (updates: PortalBrandingUpdate): Promise<PortalBranding> => {
      const { data } = await apiClient.patch<PortalBranding>('/me/branding', updates)
      return data
    },
    onSuccess: invalidate,
  })
}

export function useUploadLogo() {
  const invalidate = useInvalidateBrandingAndSession()

  return useMutation({
    mutationFn: async (file: File): Promise<PortalBranding> => {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await apiClient.put<PortalBranding>('/me/branding/logo', formData)
      return data
    },
    onSuccess: invalidate,
  })
}

export function useDeleteLogo() {
  const invalidate = useInvalidateBrandingAndSession()

  return useMutation({
    mutationFn: async (): Promise<void> => {
      await apiClient.delete('/me/branding/logo')
    },
    onSuccess: invalidate,
  })
}

export function useResetBranding() {
  const invalidate = useInvalidateBrandingAndSession()

  return useMutation({
    mutationFn: async (): Promise<PortalBranding> => {
      const { data } = await apiClient.post<PortalBranding>('/me/branding/reset')
      return data
    },
    onSuccess: invalidate,
  })
}
