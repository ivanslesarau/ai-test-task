import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

import { sessionKey } from '@/entities/session/api/use-session'
import { apiClient } from '@/shared/api/client'
import type { Impersonation, ImpersonationCreate } from '@/shared/api/types'

/**
 * `POST /admin/impersonations` (FR-040 – FR-043, FR-048). One of the
 * app's only two sanctioned `queryClient.clear()` call sites
 * (frontend-contracts.md §35): every cached response belongs to the
 * caller's own identity, and none of it may survive into the
 * impersonated portal. Navigating to `/` afterward lands on a route every
 * role can reach, regardless of which role is now effective.
 */
export function useStartImpersonation() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: async (body: ImpersonationCreate): Promise<Impersonation> => {
      const { data } = await apiClient.post<Impersonation>('/admin/impersonations', body)
      return data
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: sessionKey })
      await queryClient.clear()
      await navigate({ to: '/' })
    },
  })
}
