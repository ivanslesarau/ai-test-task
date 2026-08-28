import { useMutation, useQueryClient } from '@tanstack/react-query'

import { familyKeys } from '@/entities/player-profile/api/query-keys'
import { sessionKey } from '@/entities/session/api/use-session'
import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { CreateChildProfileRequest, PlayerProfile } from '@/shared/api/types'

/**
 * `POST /me/players` (FR-106 - FR-110, FR-122, FR-123). A near-duplicate
 * child answers with a 409 the caller reads from the mutation's own error
 * state (contracts/frontend-contracts.md §18) — this hook does not treat
 * it specially; `features/family/add-child` is what shows the dialog and
 * resubmits with `acknowledge_possible_duplicate: true`.
 */
export function useCreateChildProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateChildProfileRequest): Promise<PlayerProfile> => {
      const { data } = await apiClient.post<PlayerProfile>('/me/players', body)
      return data
    },
    onSuccess: () => {
      // A new child with trainers adds switchable pairs, so the switcher
      // and the session's context_count must both refresh
      // (contracts/frontend-contracts.md §16).
      void queryClient.invalidateQueries({ queryKey: familyKeys.profiles })
      void queryClient.invalidateQueries({ queryKey: userKeys.contexts })
      void queryClient.invalidateQueries({ queryKey: sessionKey })
    },
  })
}
