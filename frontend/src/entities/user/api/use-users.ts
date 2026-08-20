import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { userKeys } from '@/entities/user/api/query-keys'
import type { DirectorySearch } from '@/entities/user/model/directory-search'
import { apiClient } from '@/shared/api/client'
import type {
  CreatedUser,
  CreateUserRequest,
  ErasureRecord,
  UserDetail,
  UserPage,
} from '@/shared/api/types'

export function useUserDirectory(search: DirectorySearch) {
  return useQuery({
    queryKey: userKeys.directory(search),
    queryFn: async (): Promise<UserPage> => {
      const { data } = await apiClient.get<UserPage>('/admin/users', { params: search })
      return data
    },
    placeholderData: keepPreviousData,
  })
}

export function useUserDetail(userId: string) {
  return useQuery({
    queryKey: userKeys.detail(userId),
    queryFn: async (): Promise<UserDetail> => {
      const { data } = await apiClient.get<UserDetail>(`/admin/users/${userId}`)
      return data
    },
  })
}

export function useErasureRecord(userId: string, enabled: boolean) {
  return useQuery({
    queryKey: userKeys.erasureRecord(userId),
    queryFn: async (): Promise<ErasureRecord> => {
      const { data } = await apiClient.get<ErasureRecord>(`/admin/erasure-records/${userId}`)
      return data
    },
    enabled,
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (body: CreateUserRequest): Promise<CreatedUser> => {
      const { data } = await apiClient.post<CreatedUser>('/admin/users', body)
      return data
    },
    onSuccess: () => {
      // The new account's position depends on the active sort and filters,
      // so no narrower invalidation than the whole subtree is correct
      // (contracts/frontend-contracts.md §2).
      void queryClient.invalidateQueries({ queryKey: userKeys.all })
    },
  })
}

export function useReinviteUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (
      userId: string,
    ): Promise<{ invitation_sent: boolean; expires_at: string }> => {
      const { data } = await apiClient.post(`/admin/users/${userId}/reinvite`)
      return data
    },
    onSuccess: (_data, userId) => {
      void queryClient.invalidateQueries({ queryKey: userKeys.detail(userId) })
    },
  })
}
