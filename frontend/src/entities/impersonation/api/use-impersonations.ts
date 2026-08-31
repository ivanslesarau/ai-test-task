import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { impersonationKeys } from '@/entities/impersonation/api/query-keys'
import type { ImpersonationHistorySearch } from '@/entities/impersonation/model/history-search'
import { apiClient } from '@/shared/api/client'
import type { ImpersonationPage } from '@/shared/api/types'

/** `GET /admin/impersonations` (US7, FR-053, FR-054) — the append-only
 * history, filtered and paged straight from the URL-owned search
 * params. */
export function useImpersonations(search: ImpersonationHistorySearch) {
  return useQuery({
    queryKey: impersonationKeys.list(search),
    queryFn: async (): Promise<ImpersonationPage> => {
      const { data } = await apiClient.get<ImpersonationPage>('/admin/impersonations', {
        params: search,
      })
      return data
    },
    placeholderData: keepPreviousData,
  })
}
