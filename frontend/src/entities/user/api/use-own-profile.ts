import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { userKeys } from '@/entities/user/api/query-keys'
import { sessionKey } from '@/entities/session/api/use-session'
import { apiClient } from '@/shared/api/client'
import type { OwnProfile, OwnProfileUpdate, PhotoUrls } from '@/shared/api/types'

export function useOwnProfile() {
  return useQuery({
    queryKey: userKeys.ownProfile,
    queryFn: async (): Promise<OwnProfile> => {
      const { data } = await apiClient.get<OwnProfile>('/me/profile')
      return data
    },
  })
}

function useInvalidateProfileAndSession() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: userKeys.ownProfile })
    void queryClient.invalidateQueries({ queryKey: sessionKey })
  }
}

export function useUpdateOwnProfile() {
  const invalidate = useInvalidateProfileAndSession()

  return useMutation({
    mutationFn: async (updates: OwnProfileUpdate): Promise<OwnProfile> => {
      const { data } = await apiClient.patch<OwnProfile>('/me/profile', updates)
      return data
    },
    onSuccess: invalidate,
  })
}

export function useUploadOwnPhoto() {
  const invalidate = useInvalidateProfileAndSession()

  return useMutation({
    mutationFn: async (file: File): Promise<PhotoUrls> => {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await apiClient.put<PhotoUrls>('/me/profile/photo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },
    onSuccess: invalidate,
  })
}

export function useDeleteOwnPhoto() {
  const invalidate = useInvalidateProfileAndSession()

  return useMutation({
    mutationFn: async (): Promise<void> => {
      await apiClient.delete('/me/profile/photo')
    },
    onSuccess: invalidate,
  })
}
