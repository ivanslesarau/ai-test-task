import { useMutation, useQueryClient } from '@tanstack/react-query'

import { availabilityKeys } from '@/entities/availability/api/query-keys'
import { coachKeys } from '@/entities/coach/api/query-keys'
import { apiClient } from '@/shared/api/client'

/** `DELETE /trainer/coaches/{coach_user_id}` (FR-021 – FR-023). The coach
 * is on no roster afterwards, so their week is no longer disclosed to
 * this trainer either — invalidating `availabilityKeys.all` alongside
 * `coachKeys.all` is what frontend-contracts.md §31 requires. */
export function useEndCoachAssignment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (coachUserId: string): Promise<void> => {
      await apiClient.delete(`/trainer/coaches/${coachUserId}`)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: coachKeys.all })
      void queryClient.invalidateQueries({ queryKey: availabilityKeys.all })
    },
  })
}
