import { useMutation, useQueryClient } from '@tanstack/react-query'

import { familyKeys } from '@/entities/player-profile/api/query-keys'
import { sessionKey } from '@/entities/session/api/use-session'
import { ctxKeys } from '@/entities/trainer-context/api/query-keys'
import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { AddPlayerTrainerRequest, PlayerProfile } from '@/shared/api/types'

/** `POST /me/players/{profile_id}/trainers` (FR-125, FR-127, FR-128). */
export function useAddPlayerTrainer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (variables: {
      profileId: string
      body: AddPlayerTrainerRequest
    }): Promise<PlayerProfile> => {
      const { data } = await apiClient.post<PlayerProfile>(
        `/me/players/${variables.profileId}/trainers`,
        variables.body,
      )
      return data
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: familyKeys.profile(variables.profileId) })
      void queryClient.invalidateQueries({ queryKey: userKeys.contexts })
      void queryClient.invalidateQueries({ queryKey: sessionKey })
    },
  })
}

/** `DELETE /me/players/{profile_id}/trainers/{association_id}` (FR-126,
 * FR-128). Addressed by the association's own id, never the trainer's
 * (research.md R-25, R-48). */
export function useRemovePlayerTrainer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (variables: {
      profileId: string
      associationId: string
    }): Promise<void> => {
      await apiClient.delete(
        `/me/players/${variables.profileId}/trainers/${variables.associationId}`,
      )
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: familyKeys.profile(variables.profileId) })
      void queryClient.invalidateQueries({ queryKey: userKeys.contexts })
      void queryClient.invalidateQueries({ queryKey: sessionKey })
      // The active pair may have been this trainer-and-profile combination
      // (contracts/frontend-contracts.md §16).
      queryClient.removeQueries({ queryKey: ctxKeys.root })
    },
  })
}
