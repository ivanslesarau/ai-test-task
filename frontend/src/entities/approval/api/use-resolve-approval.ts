import { useMutation, useQueryClient } from '@tanstack/react-query'

import { approvalKeys } from '@/entities/approval/api/query-keys'
import { familyKeys } from '@/entities/player-profile/api/query-keys'
import { sessionKey } from '@/entities/session/api/use-session'
import { userKeys } from '@/entities/user/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { ApprovalDecisionRequest, ApprovalInfoRequest, ApprovalRequest } from '@/shared/api/types'

interface DecisionVariables extends ApprovalDecisionRequest {
  requestId: string
}

interface InfoVariables extends ApprovalInfoRequest {
  requestId: string
}

/**
 * `POST /me/approvals/{id}/approve`. A `join_trainer` approval creates an
 * association, so it invalidates everything the action touched —
 * `userKeys.contexts`, `session`, and `familyKeys.profiles` — as well as
 * the approvals namespace (contracts/frontend-contracts.md §16, FR-151).
 */
export function useApproveApproval() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ requestId, ...body }: DecisionVariables): Promise<ApprovalRequest> => {
      const { data } = await apiClient.post<ApprovalRequest>(
        `/me/approvals/${requestId}/approve`,
        body,
      )
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: approvalKeys.all })
      void queryClient.invalidateQueries({ queryKey: userKeys.contexts })
      void queryClient.invalidateQueries({ queryKey: sessionKey })
      void queryClient.invalidateQueries({ queryKey: familyKeys.profiles })
    },
  })
}

/** `POST /me/approvals/{id}/deny`. The action is not carried out, so
 * only the request itself changes. */
export function useDenyApproval() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ requestId, ...body }: DecisionVariables): Promise<ApprovalRequest> => {
      const { data } = await apiClient.post<ApprovalRequest>(
        `/me/approvals/${requestId}/deny`,
        body,
      )
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: approvalKeys.all })
    },
  })
}

/** `POST /me/approvals/{id}/request-info`. `note` is required — asking
 * for more information without saying what is wanted is not a message
 * (FR-150). */
export function useRequestInfoOnApproval() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ requestId, ...body }: InfoVariables): Promise<ApprovalRequest> => {
      const { data } = await apiClient.post<ApprovalRequest>(
        `/me/approvals/${requestId}/request-info`,
        body,
      )
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: approvalKeys.all })
    },
  })
}
