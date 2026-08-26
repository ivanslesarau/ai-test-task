import { describe, expect, it } from 'vitest'

import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'

describe('normalizeEmptyToNull', () => {
  it('converts an empty string to null', () => {
    expect(normalizeEmptyToNull('')).toBeNull()
  })

  it('converts a whitespace-only string to null', () => {
    expect(normalizeEmptyToNull('   \t\n ')).toBeNull()
  })

  it('passes a non-empty string through unchanged, without trimming', () => {
    expect(normalizeEmptyToNull('  Hello  ')).toBe('  Hello  ')
  })

  it('passes non-string values through unchanged', () => {
    expect(normalizeEmptyToNull(42)).toBe(42)
    expect(normalizeEmptyToNull(true)).toBe(true)
    expect(normalizeEmptyToNull(null)).toBeNull()
    expect(normalizeEmptyToNull(undefined)).toBeUndefined()
  })

  it('recurses through nested objects', () => {
    expect(normalizeEmptyToNull({ a: '', b: 'kept', c: { d: '  ' } })).toEqual({
      a: null,
      b: 'kept',
      c: { d: null },
    })
  })

  it('recurses through arrays, including arrays of objects', () => {
    expect(normalizeEmptyToNull(['', 'x', { a: '' }])).toEqual([null, 'x', { a: null }])
  })

  it('leaves a Date instance untouched', () => {
    const date = new Date('2026-01-01T00:00:00Z')
    expect(normalizeEmptyToNull(date)).toBe(date)
  })
})
