import type { OwnProfileUpdateValues } from '@/features/profile/edit-own/model/schema'
import type { OwnProfile } from '@/shared/api/types'

type FieldValue = string | boolean

const COMMON_FIELDS = new Set(['first_name', 'last_name', 'phone'])

/** Reads a field's current value from the profile, dispatching between
 * the common columns and the role_detail union without ever casting to
 * `any` — role_detail's members share no fields, so every access goes
 * through an `in` check. */
export function getFieldValue(profile: OwnProfile, field: string): FieldValue {
  if (COMMON_FIELDS.has(field)) {
    const value = profile[field as 'first_name' | 'last_name' | 'phone']
    return value ?? ''
  }
  const detail = profile.role_detail
  if (detail && field in detail) {
    const value = (detail as unknown as Record<string, unknown>)[field]
    if (typeof value === 'boolean') return value
    return typeof value === 'string' ? value : ''
  }
  return ''
}

/** `editable_fields` is a runtime-chosen subset of `OwnProfileUpdateValues`'s
 * keys (the server enforces that invariant), so the built record is safe to
 * hand back as that type — this is what lets the form's inferred value type
 * line up with `ownProfileUpdateSchema`'s output type instead of a bare
 * index signature. */
export function buildDefaultValues(profile: OwnProfile): OwnProfileUpdateValues {
  const values: Record<string, FieldValue> = {}
  for (const field of profile.editable_fields) {
    values[field] = getFieldValue(profile, field)
  }
  return values as OwnProfileUpdateValues
}
