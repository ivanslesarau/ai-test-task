import type { DirectorySearch } from '@/entities/user/model/directory-search'

/**
 * Single source of truth for every user-related query key
 * (contracts/frontend-contracts.md §2). Invalidation contract:
 *
 * | Mutation                       | Invalidates                                    |
 * |---------------------------------|-------------------------------------------------|
 * | updateOwnProfile                | ownProfile, session                             |
 * | uploadOwnPhoto / deleteOwnPhoto | ownProfile, session                             |
 * | createUser                      | all (position depends on active sort/filters)   |
 * | deactivateUser / reactivateUser | detail(userId), all                             |
 * | eraseUser                       | detail(userId), all, erasureRecord(userId)      |
 * | reinviteUser                    | detail(userId)                                  |
 */
export const userKeys = {
  all: ['users'] as const,
  ownProfile: ['users', 'me', 'profile'] as const,
  directory: (search: DirectorySearch) => ['users', 'directory', search] as const,
  detail: (userId: string) => ['users', 'detail', userId] as const,
  audit: (userId: string, page: number) => ['users', 'audit', userId, page] as const,
  erasureRecord: (userId: string) => ['users', 'erasure', userId] as const,
  // Extension (2026-08-26) — a trainer's own keys, not context-scoped
  // (contracts/frontend-contracts.md §9).
  trainers: ['users', 'me', 'trainers'] as const,
  shareLink: ['users', 'me', 'share-link'] as const,
  branding: ['users', 'me', 'branding'] as const,
} as const
