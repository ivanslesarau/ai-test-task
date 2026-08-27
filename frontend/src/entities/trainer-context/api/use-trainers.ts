import { useQuery } from '@tanstack/react-query'

import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { TrainerContextList } from '@/shared/api/types'

export function useOwnTrainers() {
  return useQuery({
    queryKey: userKeys.trainers,
    queryFn: async (): Promise<TrainerContextList> => {
      const { data } = await apiClient.get<TrainerContextList>('/me/trainers')
      return data
    },
  })
}
