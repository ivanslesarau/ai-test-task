/**
 * Family accounts (US9, US10; contracts/frontend-contracts.md §16). One
 * factory, imported by every slice that reads or writes a family's own
 * player profiles — mirrors how `userKeys` centralizes account keys.
 */
export const familyKeys = {
  all: ['family'] as const,
  profiles: ['family', 'profiles'] as const,
  profile: (profileId: string) => ['family', 'profiles', profileId] as const,
} as const
