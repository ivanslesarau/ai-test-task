import { describe, expect, it } from 'vitest'

import { apiClient } from '@/shared/api/client'
import { resolveMediaUrl } from '@/shared/api/media'

describe('resolveMediaUrl', () => {
  it('returns null for a null path', () => {
    expect(resolveMediaUrl(null)).toBeNull()
  })

  it('prefixes the path with the axios baseURL', () => {
    expect(resolveMediaUrl('/media/photos/abc.jpg')).toBe(
      `${apiClient.defaults.baseURL}/media/photos/abc.jpg`,
    )
  })
})
