import { isApiError } from '@/shared/api/errors'

/** A Standard Schema issue (what Zod, and TanStack Form's `onDynamic`/
 * `onSubmit` validators, attach to `field.state.meta.errors`) carries a
 * `message` string. A plain string is also a valid entry — TanStack Form
 * accepts either — but the inline `errors.map((e) => e?.message).join(', ')`
 * pattern silently renders nothing for a string-valued entry, since a
 * string has no `.message`. This narrows `unknown` once instead of at
 * every call site (constitution Principle II). */
function hasMessage(value: unknown): value is { message: string } {
  return (
    typeof value === 'object' &&
    value !== null &&
    'message' in value &&
    typeof (value as { message: unknown }).message === 'string'
  )
}

/** The first renderable message among a field's errors, or `null` when
 * there is nothing to show. */
export function fieldErrorText(errors: readonly unknown[]): string | null {
  for (const error of errors) {
    if (typeof error === 'string' && error.length > 0) return error
    if (hasMessage(error)) return error.message
  }
  return null
}

/** The shape TanStack Form's `onServer` validation slot expects: a
 * form-level message and/or a map of field name to message. Forms declare
 * `validators: { onServer: () => undefined as ServerErrorMap | undefined }`
 * purely so `TOnServerReturn` is inferred as this type — the validator
 * itself never runs; `form.setErrorMap({ onServer: toServerErrorMap(error) })`
 * in a mutation's `onError` is what actually populates it. */
export type ServerErrorMap = { form?: string; fields: Record<string, string> }

/** Builds the object TanStack Form's `form.setErrorMap({ onServer: ... })`
 * expects: a form-level message and/or a map of field name to message,
 * built from `ApiError.fields` (contracts/frontend-contracts.md §3, §7.2).
 * No form reads `ApiError.fields` directly. */
export function toServerErrorMap(error: unknown): ServerErrorMap {
  if (!isApiError(error)) {
    return { form: 'An unexpected error occurred.', fields: {} }
  }
  if (error.fields.length === 0) {
    return { form: error.message, fields: {} }
  }
  const fields: Record<string, string> = {}
  for (const fieldError of error.fields) {
    fields[fieldError.field] = fieldError.message
  }
  return { fields }
}
