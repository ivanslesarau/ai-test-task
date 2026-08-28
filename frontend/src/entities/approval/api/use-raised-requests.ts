import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { approvalKeys } from '@/entities/approval/api/query-keys'
import type { ApprovalSearch } from '@/entities/approval/model/approval-search'
import { apiClient } from '@/shared/api/client'
import type { ApprovalRequestPage } from '@/shared/api/types'

/** The child's own view of what they asked for, `GET /me/requests`
 * (FR-153). Omitted `status` returns every status, newest first. */
export function useRaisedRequests(search: ApprovalSearch) {
  return useQuery({
    queryKey: approvalKeys.raised(search),
    queryFn: async (): Promise<ApprovalRequestPage> => {
      const { data } = await apiClient.get<ApprovalRequestPage>('/me/requests', {
        params: search,
      })
      return data
    },
    placeholderData: keepPreviousData,
  })
}
