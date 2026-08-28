import { useMutation, useQueryClient } from '@tanstack/react-query'

import { ctxKeys } from '@/entities/trainer-context/api/query-keys'
import { sessionKey } from '@/entities/session/api/use-session'
import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { TrainingContextList } from '@/shared/api/types'

/**
 * The only way context changes on the client, mirroring the server's one
 * endpoint (research.md R-25, R-48). On success: update the contexts list
 * from the response, drop every context-scoped cache entry, *then* let
 * the session refetch resolve the new branding — dropping the `ctx`
 * namespace before the session settles is what stops a frame rendering
 * from the previous pair's cache, which FR-087 forbids (R-26, R-47).
 */
export function useSwitchTrainingContext() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (pair: {
      playerProfileId: string
      trainerId: string
    }): Promise<TrainingContextList> => {
      const { data } = await apiClient.put<TrainingContextList>('/me/context', {
        player_profile_id: pair.playerProfileId,
        trainer_id: pair.trainerId,
      })
      return data
    },
    onSuccess: (data) => {
      queryClient.setQueryData(userKeys.contexts, data)
      queryClient.removeQueries({ queryKey: ctxKeys.root })
      void queryClient.invalidateQueries({ queryKey: sessionKey })
    },
  })
}
