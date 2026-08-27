import { useQuery } from '@tanstack/react-query'

import { ctxKeys } from '@/entities/trainer-context/api/query-keys'
import type { RosterSearch } from '@/entities/trainer-context/model/roster-search'
import { apiClient } from '@/shared/api/client'
import type { TrainerPlayerPage } from '@/shared/api/types'

/**
 * The trainer's own roster. Keyed under the `ctx` namespace by the
 * trainer's own id — the standing convention (research.md R-26) every
 * trainer-scoped data view follows, so a future player-side reader of the
 * same endpoint composes with it rather than inventing a second key
 * shape.
 */
export function useTrainerRoster(trainerId: string, search: RosterSearch) {
  return useQuery({
    queryKey: ctxKeys.players(trainerId, search),
    queryFn: async (): Promise<TrainerPlayerPage> => {
      const { data } = await apiClient.get<TrainerPlayerPage>('/trainer/players', {
        params: search,
      })
      return data
    },
  })
}
