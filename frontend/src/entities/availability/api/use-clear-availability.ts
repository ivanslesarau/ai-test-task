import { useMutation, useQueryClient } from '@tanstack/react-query'

import type { WritableAvailabilitySubject } from '@/entities/availability/api/query-keys'
import { availabilityKeys, availabilitySubjectUrl } from '@/entities/availability/api/query-keys'
import { apiClient } from '@/shared/api/client'

/** `DELETE /me/availability` or `DELETE /me/players/{profile_id}/availability`
 * (FR-030, FR-032). Distinct from a save of an empty week only in intent
 * — both stamp `updated_at` — but kept as its own mutation because "I have
 * no times to offer" is a deliberate action, not a side effect of editing. */
export function useClearAvailability(subject: WritableAvailabilitySubject) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (): Promise<void> => {
      await apiClient.delete(availabilitySubjectUrl(subject))
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: availabilityKeys.week(subject) })
    },
  })
}
