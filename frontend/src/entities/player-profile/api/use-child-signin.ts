import { useMutation, useQueryClient } from '@tanstack/react-query'

import { familyKeys } from '@/entities/player-profile/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { ChildSignIn, GrantChildSignInRequest } from '@/shared/api/types'

/**
 * `PUT /me/players/{profile_id}/sign-in` (US11, FR-129, FR-130). Only for
 * a `child` profile, and only for the owning parent — the server is the
 * actual barrier (FR-132, FR-133); this mutation just carries the
 * request.
 */
export function useGrantChildSignIn() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (variables: {
      profileId: string
      body: GrantChildSignInRequest
    }): Promise<ChildSignIn> => {
      const { data } = await apiClient.put<ChildSignIn>(
        `/me/players/${variables.profileId}/sign-in`,
        variables.body,
      )
      return data
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: familyKeys.profile(variables.profileId) })
    },
  })
}

/**
 * `DELETE /me/players/{profile_id}/sign-in` (US11, FR-134). Ends the
 * child's own way in; their profile, trainers, and history are untouched.
 */
export function useRevokeChildSignIn() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (profileId: string): Promise<void> => {
      await apiClient.delete(`/me/players/${profileId}/sign-in`)
    },
    onSuccess: (_data, profileId) => {
      void queryClient.invalidateQueries({ queryKey: familyKeys.profile(profileId) })
    },
  })
}
