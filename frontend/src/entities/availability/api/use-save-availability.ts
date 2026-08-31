import { useMutation, useQueryClient } from '@tanstack/react-query'

import type { WritableAvailabilitySubject } from '@/entities/availability/api/query-keys'
import { availabilityKeys, availabilitySubjectUrl } from '@/entities/availability/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { AvailabilityWeek, AvailabilityWeekUpdate } from '@/shared/api/types'

/** `PUT /me/availability` or `PUT /me/players/{profile_id}/availability`
 * — the whole-week replace (FR-029). Invalidates only this subject's own
 * key (frontend-contracts.md §31): a parent saving one child's week must
 * not refetch a sibling's. */
export function useSaveAvailability(subject: WritableAvailabilitySubject) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (update: AvailabilityWeekUpdate): Promise<AvailabilityWeek> => {
      const { data } = await apiClient.put<AvailabilityWeek>(
        availabilitySubjectUrl(subject),
        update,
      )
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: availabilityKeys.week(subject) })
    },
  })
}
