import { describe, expect, it } from 'vitest'

import {
  availabilityKeys,
  availabilitySubjectUrl,
} from '@/entities/availability/api/query-keys'

describe('availabilityKeys', () => {
  it('gives each subject kind its own key', () => {
    const own = availabilityKeys.week({ kind: 'own' })
    const profileA = availabilityKeys.week({ kind: 'profile', profileId: 'grace' })
    const profileB = availabilityKeys.week({ kind: 'profile', profileId: 'leo' })

    expect(own).not.toEqual(profileA)
    // Invalidation is per subject (frontend-contracts.md §31): saving
    // Grace's week must never carry a query key that also matches Leo's.
    expect(profileA).not.toEqual(profileB)
  })

  it('gives the same subject the same key on every call', () => {
    const first = availabilityKeys.week({ kind: 'profile', profileId: 'grace' })
    const second = availabilityKeys.week({ kind: 'profile', profileId: 'grace' })
    expect(first).toEqual(second)
  })
})

describe('availabilitySubjectUrl', () => {
  it('resolves the own subject to /me/availability', () => {
    expect(availabilitySubjectUrl({ kind: 'own' })).toBe('/me/availability')
  })

  it('resolves a profile subject to the nested family route', () => {
    expect(availabilitySubjectUrl({ kind: 'profile', profileId: 'grace' })).toBe(
      '/me/players/grace/availability',
    )
  })

  it('resolves the trainer-facing coach subject', () => {
    expect(availabilitySubjectUrl({ kind: 'coach-as-trainer', coachUserId: 'cody' })).toBe(
      '/trainer/coaches/cody/availability',
    )
  })

  it('resolves the trainer-facing player subject', () => {
    expect(availabilitySubjectUrl({ kind: 'player-as-trainer', profileId: 'leo' })).toBe(
      '/trainer/players/leo/availability',
    )
  })
})
