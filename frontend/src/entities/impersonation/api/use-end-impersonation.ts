import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

import { sessionKey } from '@/entities/session/api/use-session'
import { apiClient } from '@/shared/api/client'

/**
 * `DELETE /admin/impersonations/current` (FR-045, FR-046, research.md
 * R2-15). The second of the app's two sanctioned `queryClient.clear()`
 * call sites (frontend-contracts.md §35) — a Super Admin's cached
 * directory page must not survive back into their own portal any more
 * than it may survive into the impersonated one.
 */
export function useEndImpersonation() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: async (): Promise<void> => {
      await apiClient.delete('/admin/impersonations/current')
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: sessionKey })
      await queryClient.clear()
      await navigate({ to: '/' })
    },
  })
}
