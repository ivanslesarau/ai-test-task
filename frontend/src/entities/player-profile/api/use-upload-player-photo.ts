import { useMutation, useQueryClient } from '@tanstack/react-query'

import { familyKeys } from '@/entities/player-profile/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { PhotoUrls } from '@/shared/api/types'

/** `PUT /me/players/{profile_id}/photo` (FR-034, FR-131, R-07). */
export function useUploadPlayerPhoto() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (variables: { profileId: string; file: File }): Promise<PhotoUrls> => {
      const formData = new FormData()
      formData.append('file', variables.file)
      const { data } = await apiClient.put<PhotoUrls>(
        `/me/players/${variables.profileId}/photo`,
        formData,
      )
      return data
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: familyKeys.profile(variables.profileId) })
      void queryClient.invalidateQueries({ queryKey: familyKeys.profiles })
    },
  })
}
