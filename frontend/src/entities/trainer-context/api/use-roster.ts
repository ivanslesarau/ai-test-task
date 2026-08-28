import { useQuery } from '@tanstack/react-query'

import type { RosterSearch } from '@/entities/trainer-context/model/roster-search'
import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { TrainerPlayerPage } from '@/shared/api/types'

/**
 * The trainer's own roster. Keyed under `userKeys.roster`, **not** the
 * `ctx` namespace (tasks.md T337) — a trainer has no profile-and-trainer
 * pair of their own to key it by, and R-47's profile dimension exists to
 * isolate one *player's* sibling from another, which has no bearing on a
 * trainer's own view of their players.
 */
export function useTrainerRoster(search: RosterSearch) {
  return useQuery({
    queryKey: userKeys.roster(search),
    queryFn: async (): Promise<TrainerPlayerPage> => {
      const { data } = await apiClient.get<TrainerPlayerPage>('/trainer/players', {
        params: search,
      })
      return data
    },
  })
}
