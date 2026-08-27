import { queryOptions, useQuery } from '@tanstack/react-query'

import { joinKeys } from '@/entities/join/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { JoinLinkPreview } from '@/shared/api/types'

export function joinPreviewQueryOptions(code: string) {
  return queryOptions({
    queryKey: joinKeys.preview(code),
    queryFn: async (): Promise<JoinLinkPreview> => {
      const { data } = await apiClient.get<JoinLinkPreview>(`/join/${code}`)
      return data
    },
    retry: false,
  })
}

export function useJoinPreview(code: string) {
  return useQuery(joinPreviewQueryOptions(code))
}
