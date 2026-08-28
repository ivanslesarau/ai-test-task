import { describe, expect, it } from 'vitest'

import { ctxKeys } from '@/entities/trainer-context/api/query-keys'
import { userKeys } from '@/entities/user/api/query-keys'

/**
 * research.md R-26, R-47: every query key touching one player profile's
 * training data begins `['ctx', profileId, trainerId]` — the pair is the
 * isolation boundary a sibling collides across, not the trainer alone
 * (FR-117, tasks.md T337).
 *
 * The trainer's own roster is not context-scoped this way — a trainer
 * has no profile-and-trainer pair of their own — and lives under
 * `userKeys.roster` instead.
 */
describe('ctxKeys — the context namespace convention', () => {
  it('root is exactly ["ctx"]', () => {
    expect(ctxKeys.root).toEqual(['ctx'])
  })

  it('scope begins with the namespace, the profile id, and the trainer id', () => {
    const key = ctxKeys.scope('profile-1', 'trainer-1')
    expect(key[0]).toBe('ctx')
    expect(key[1]).toBe('profile-1')
    expect(key[2]).toBe('trainer-1')
  })

  it('two different profiles never collide on the same key, even with the same trainer', () => {
    const keyA = ctxKeys.scope('profile-a', 'trainer-1')
    const keyB = ctxKeys.scope('profile-b', 'trainer-1')
    expect(JSON.stringify(keyA)).not.toBe(JSON.stringify(keyB))
  })

  it('two different trainers never collide on the same key, even with the same profile', () => {
    const keyA = ctxKeys.scope('profile-1', 'trainer-a')
    const keyB = ctxKeys.scope('profile-1', 'trainer-b')
    expect(JSON.stringify(keyA)).not.toBe(JSON.stringify(keyB))
  })
})

describe('userKeys.roster — moved out of the ctx namespace', () => {
  it('does not begin with the ctx namespace', () => {
    const key = userKeys.roster({ page: 1, page_size: 25 })
    expect(key[0]).not.toBe('ctx')
    expect(key[0]).toBe('users')
  })
})
