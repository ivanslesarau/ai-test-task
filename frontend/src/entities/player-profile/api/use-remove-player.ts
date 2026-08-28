import { useMutation, useQueryClient } from '@tanstack/react-query'

import { familyKeys } from '@/entities/player-profile/api/query-keys'
import { sessionKey } from '@/entities/session/api/use-session'
import { ctxKeys } from '@/entities/trainer-context/api/query-keys'
import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'

/**
 * `DELETE /me/players/{profile_id}` (FR-111, FR-135). A soft removal —
 * every historical record survives server-side; the client's job is
 * dropping every cache entry that could still name the removed profile.
 */
export function useRemovePlayerProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (profileId: string): Promise<void> => {
      await apiClient.delete(`/me/players/${profileId}`)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: familyKeys.profiles })
      void queryClient.invalidateQueries({ queryKey: userKeys.contexts })
      void queryClient.invalidateQueries({ queryKey: sessionKey })
      // The active pair may have named the profile just removed — never
      // served from a stale cache entry (contracts/frontend-contracts.md
      // §16).
      queryClient.removeQueries({ queryKey: ctxKeys.root })
    },
  })
}
