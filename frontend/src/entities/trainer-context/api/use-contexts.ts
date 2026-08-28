import { useQuery } from '@tanstack/react-query'

import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { TrainingContextList } from '@/shared/api/types'

/**
 * Replaces `useOwnTrainers` (research.md R-49) — every entry now names
 * both the player profile and the trainer (FR-117, FR-118).
 */
export function useOwnContexts() {
  return useQuery({
    queryKey: userKeys.contexts,
    queryFn: async (): Promise<TrainingContextList> => {
      const { data } = await apiClient.get<TrainingContextList>('/me/contexts')
      return data
    },
  })
}
