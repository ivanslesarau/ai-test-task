/**
 * The single empty-string-to-null normalizer (constitution Principle VI).
 *
 * React controlled inputs initialize optional fields to `''`. That is a
 * rendering artifact, not "no value" — the network and the database both
 * spell "no value" as `null`. Every TanStack Form submit handler MUST pass
 * its values through this helper before the payload reaches `axios`. No
 * other normalizer, and no per-form ternary at a call site, is permitted to
 * exist.
 *
 * Rules:
 * - A string that is empty or contains only whitespace becomes `null`.
 * - Any other string passes through unchanged — trimming a real value, if
 *   ever wanted, belongs in the field's Zod schema, not here.
 * - Arrays and plain objects are recursed into; every other value (numbers,
 *   booleans, `null`, `undefined`, `Date`, etc.) passes through unchanged.
 */
export function normalizeEmptyToNull<T>(value: T): T {
  if (typeof value === 'string') {
    return (value.trim() === '' ? null : value) as unknown as T
  }
  if (Array.isArray(value)) {
    return value.map((item: unknown) => normalizeEmptyToNull(item)) as unknown as T
  }
  if (value !== null && typeof value === 'object' && !(value instanceof Date)) {
    const result: Record<string, unknown> = {}
    for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
      result[key] = normalizeEmptyToNull(entry)
    }
    return result as unknown as T
  }
  return value
}
