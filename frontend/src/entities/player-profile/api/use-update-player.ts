import { useMutation, useQueryClient } from '@tanstack/react-query'

import { familyKeys } from '@/entities/player-profile/api/query-keys'
import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { PlayerProfile, PlayerProfileUpdate } from '@/shared/api/types'

/** `PATCH /me/players/{profile_id}` (FR-107, FR-131, FR-132, FR-147). */
export function useUpdatePlayerProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (variables: {
      profileId: string
      body: PlayerProfileUpdate
    }): Promise<PlayerProfile> => {
      const { data } = await apiClient.patch<PlayerProfile>(
        `/me/players/${variables.profileId}`,
        variables.body,
      )
      return data
    },
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: familyKeys.profile(variables.profileId) })
      void queryClient.invalidateQueries({ queryKey: familyKeys.profiles })
      // The switcher shows a profile's display_name (contracts/
      // frontend-contracts.md §16 and §19) — invalidating unconditionally
      // rather than only when a name field was in the payload is a safe
      // superset of the contract's "when the name changed" clause: a
      // refetch of an unchanged name costs a request, a stale name in the
      // switcher does not self-correct.
      void queryClient.invalidateQueries({ queryKey: userKeys.contexts })
    },
  })
}
