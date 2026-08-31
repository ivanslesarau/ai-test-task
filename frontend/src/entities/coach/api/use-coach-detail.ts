import { useQuery } from '@tanstack/react-query'

import { coachKeys } from '@/entities/coach/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { TrainerCoachPage, TrainerCoachSummary } from '@/shared/api/types'

/** No dedicated `GET /trainer/coaches/{id}` exists in `contracts/openapi.yaml`
 * — the roster page is the only source of one coach's profile summary
 * and stated week (both already embedded per row, research.md R2-12).
 * Reads a single page sized to the platform's maximum (100), which
 * comfortably covers one trainer's coaching staff, and picks out the
 * matching row client-side rather than adding a second backend
 * endpoint for what the list already returns in full (US5, T611).
 *
 * Throws — rather than resolving `undefined` — when no row matches, so
 * TanStack Query's `isError` reflects "this coach is not on your roster"
 * instead of silently caching an `undefined` result (a query function
 * resolving `undefined` is a TanStack Query contract violation). */
export function useCoachDetail(coachUserId: string) {
  return useQuery({
    queryKey: coachKeys.detail(coachUserId),
    queryFn: async (): Promise<TrainerCoachSummary> => {
      const { data } = await apiClient.get<TrainerCoachPage>('/trainer/coaches', {
        params: { page: 1, page_size: 100 },
      })
      const coach = data.items.find((item) => item.user_id === coachUserId)
      if (coach === undefined) throw new Error('No such coach on your roster.')
      return coach
    },
  })
}
