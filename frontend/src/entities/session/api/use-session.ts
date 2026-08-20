import { queryOptions, useQuery } from '@tanstack/react-query'

import { apiClient } from '@/shared/api/client'
import type { CurrentUser } from '@/shared/api/types'

export const sessionKey = ['session'] as const

export const sessionQueryOptions = queryOptions({
  queryKey: sessionKey,
  queryFn: async (): Promise<CurrentUser> => {
    const { data } = await apiClient.get<CurrentUser>('/auth/session')
    return data
  },
  retry: false,
})

export function useSession() {
  return useQuery(sessionQueryOptions)
}
