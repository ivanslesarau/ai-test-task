import { useQuery } from '@tanstack/react-query'

import { familyKeys } from '@/entities/player-profile/api/query-keys'
import { apiClient } from '@/shared/api/client'
import type { PlayerProfile, PlayerProfileList } from '@/shared/api/types'

/** The family list — the account holder's own profile, when they train,
 * alongside every child (FR-106, FR-124). A signed-in child receives only
 * their own profile; the scoping happens server-side (FR-132, R-48). */
export function useFamilyProfiles() {
  return useQuery({
    queryKey: familyKeys.profiles,
    queryFn: async (): Promise<PlayerProfileList> => {
      const { data } = await apiClient.get<PlayerProfileList>('/me/players')
      return data
    },
  })
}

/** One profile and its trainers — the `/family/$profileId` detail view. */
export function useFamilyProfile(profileId: string) {
  return useQuery({
    queryKey: familyKeys.profile(profileId),
    queryFn: async (): Promise<PlayerProfile> => {
      const { data } = await apiClient.get<PlayerProfile>(`/me/players/${profileId}`)
      return data
    },
    enabled: profileId.length > 0,
  })
}
