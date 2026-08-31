import { useQuery } from '@tanstack/react-query'

import type { AvailabilitySubject } from '@/entities/availability/api/query-keys'
import { availabilityKeys, availabilitySubjectUrl } from '@/entities/availability/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { AvailabilityWeek } from '@/shared/api/types'

/** One hook, taking an `AvailabilitySubject` (frontend-contracts.md §34)
 * — the coach's own week, a player profile's week, or (US5, later) either
 * trainer-facing read. A never-stated week reads as `{slots: [],
 * updated_at: null}` — "no times set", not "unavailable" (FR-035). */
export function useAvailability(subject: AvailabilitySubject) {
  return useQuery({
    queryKey: availabilityKeys.week(subject),
    queryFn: async (): Promise<AvailabilityWeek> => {
      const { data } = await apiClient.get<AvailabilityWeek>(availabilitySubjectUrl(subject))
      return data
    },
  })
}
