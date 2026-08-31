import { keepPreviousData, useQuery } from '@tanstack/react-query'

import type { CoachRosterParams } from '@/entities/coach/api/query-keys'
import { coachKeys } from '@/entities/coach/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { TrainerCoachPage } from '@/shared/api/types'

/** `GET /trainer/coaches` (FR-020, FR-034, FR-036) — the trainer's own
 * roster, each row already carrying its stated week (research.md R2-12),
 * so the table never fetches availability per row. */
export function useTrainerCoaches(params: CoachRosterParams) {
  return useQuery({
    queryKey: coachKeys.roster(params),
    queryFn: async (): Promise<TrainerCoachPage> => {
      const { data } = await apiClient.get<TrainerCoachPage>('/trainer/coaches', { params })
      return data
    },
    placeholderData: keepPreviousData,
  })
}
