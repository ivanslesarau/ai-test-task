import { useMutation, useQueryClient } from '@tanstack/react-query'

import { approvalKeys } from '@/entities/approval/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { ApprovalInfoRequest, ApprovalRequest } from '@/shared/api/types'

interface RespondVariables extends ApprovalInfoRequest {
  requestId: string
}

/** `POST /me/requests/{id}/respond` — only from `info_requested`, back
 * to `pending_parent_approval`, without restarting the deadline
 * (FR-143, FR-155). `note` is required. */
export function useRespondToRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ requestId, ...body }: RespondVariables): Promise<ApprovalRequest> => {
      const { data } = await apiClient.post<ApprovalRequest>(
        `/me/requests/${requestId}/respond`,
        body,
      )
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: approvalKeys.all })
    },
  })
}
