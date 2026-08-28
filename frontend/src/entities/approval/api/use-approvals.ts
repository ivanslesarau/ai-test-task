import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { approvalKeys } from '@/entities/approval/api/query-keys'
import type { ApprovalSearch } from '@/entities/approval/model/approval-search'
import { apiClient } from '@/shared/api/client'
import type { ApprovalRequest, ApprovalRequestPage } from '@/shared/api/types'

/** The parent's decision queue, `GET /me/approvals` (FR-149). Defaults
 * to the live statuses server-side when `status` is omitted. `enabled`
 * lets a caller that only needs the pending count (the nav frame's
 * badge, FR-159) skip the request entirely for a caller with nothing to
 * decide, e.g. a signed-in child. */
export function useApprovals(search: ApprovalSearch, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: approvalKeys.queue(search),
    queryFn: async (): Promise<ApprovalRequestPage> => {
      const { data } = await apiClient.get<ApprovalRequestPage>('/me/approvals', {
        params: search,
      })
      return data
    },
    placeholderData: keepPreviousData,
    enabled: options.enabled,
  })
}

export function useApprovalDetail(requestId: string) {
  return useQuery({
    queryKey: approvalKeys.detail(requestId),
    queryFn: async (): Promise<ApprovalRequest> => {
      const { data } = await apiClient.get<ApprovalRequest>(`/me/approvals/${requestId}`)
      return data
    },
  })
}
