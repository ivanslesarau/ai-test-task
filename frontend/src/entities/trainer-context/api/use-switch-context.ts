import { useMutation, useQueryClient } from '@tanstack/react-query'

import { ctxKeys } from '@/entities/trainer-context/api/query-keys'
import { sessionKey } from '@/entities/session/api/use-session'
import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { TrainerContextList } from '@/shared/api/types'

/**
 * The only way context changes on the client, mirroring the server's one
 * endpoint (research.md R-25). On success: update the trainers list from
 * the response, drop every context-scoped cache entry, *then* let the
 * session refetch resolve the new branding — dropping the `ctx`
 * namespace before the session settles is what stops a frame rendering
 * from the previous trainer's cache, which FR-087 forbids (R-26).
 */
export function useSwitchTrainerContext() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (trainerId: string): Promise<TrainerContextList> => {
      const { data } = await apiClient.put<TrainerContextList>('/me/trainer-context', {
        trainer_id: trainerId,
      })
      return data
    },
    onSuccess: (data) => {
      queryClient.setQueryData(userKeys.trainers, data)
      queryClient.removeQueries({ queryKey: ctxKeys.root })
      void queryClient.invalidateQueries({ queryKey: sessionKey })
    },
  })
}
