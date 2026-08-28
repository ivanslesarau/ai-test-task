import { useMutation, useQueryClient } from '@tanstack/react-query'

import { approvalKeys } from '@/entities/approval/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { ApprovalRequest } from '@/shared/api/types'

/** `POST /me/requests/{id}/withdraw` — only the child the request
 * concerns, and only while it is still live (FR-154). */
export function useWithdrawRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (requestId: string): Promise<ApprovalRequest> => {
      const { data } = await apiClient.post<ApprovalRequest>(
        `/me/requests/${requestId}/withdraw`,
      )
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: approvalKeys.all })
    },
  })
}
