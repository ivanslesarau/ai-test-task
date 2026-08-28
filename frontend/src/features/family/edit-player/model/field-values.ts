import type { PlayerProfileUpdateValues } from '@/features/family/edit-player/model/schema'
import type { PlayerProfile } from '@/shared/api/types'

/**
 * Which fields this form renders for `profile`, and their starting
 * values — the single place that expresses "name fields only for a
 * `child`, `tokens_without_approval` only away from a `self` profile"
 * (research.md R-37; a `self` profile's token setting is always false and
 * unwritable, contracts/openapi.yaml `PlayerProfile.tokens_without_approval`).
 */
export function buildDefaultValues(profile: PlayerProfile): PlayerProfileUpdateValues {
  const values: PlayerProfileUpdateValues = {
    date_of_birth: profile.date_of_birth ?? '',
    gender: (profile.gender as PlayerProfileUpdateValues['gender']) ?? undefined,
    school: profile.school ?? '',
    jersey_number: profile.jersey_number ?? '',
  }

  if (profile.kind === 'child') {
    values.first_name = profile.first_name ?? ''
    values.last_name = profile.last_name ?? ''
    values.tokens_without_approval = profile.tokens_without_approval
  }

  return values
}

export function editableFieldNames(profile: PlayerProfile): (keyof PlayerProfileUpdateValues)[] {
  return Object.keys(buildDefaultValues(profile)) as (keyof PlayerProfileUpdateValues)[]
}
