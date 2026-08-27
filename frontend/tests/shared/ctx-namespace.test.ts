import { describe, expect, it } from 'vitest'

import { ctxKeys } from '@/entities/trainer-context/api/query-keys'

/**
 * research.md R-26: every query key touching trainer-scoped data begins
 * `['ctx', trainerId]`. The convention is only worth fixing now — while
 * it holds one entry (the roster) — if it is enforced now; Epics 02-08
 * inherit whatever this test locks in.
 */
describe('ctxKeys — the context namespace convention', () => {
  it('root is exactly ["ctx"]', () => {
    expect(ctxKeys.root).toEqual(['ctx'])
  })

  it('scope begins with the namespace and the trainer id', () => {
    const key = ctxKeys.scope('trainer-1')
    expect(key[0]).toBe('ctx')
    expect(key[1]).toBe('trainer-1')
  })

  it('players begins with the namespace and the trainer id', () => {
    const key = ctxKeys.players('trainer-1', { page: 1, page_size: 25 })
    expect(key[0]).toBe('ctx')
    expect(key[1]).toBe('trainer-1')
  })

  it('two different trainers never collide on the same key', () => {
    const search = { page: 1, page_size: 25 }
    const keyA = ctxKeys.players('trainer-a', search)
    const keyB = ctxKeys.players('trainer-b', search)
    expect(JSON.stringify(keyA)).not.toBe(JSON.stringify(keyB))
  })
})
