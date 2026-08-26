import { renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useDebouncedCallback } from '@/shared/lib/use-debounced-callback'

describe('useDebouncedCallback', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('invokes the callback exactly once for a rapid burst of calls', () => {
    const fn = vi.fn()
    const { result } = renderHook(() => useDebouncedCallback(fn, 500))

    result.current('a')
    result.current('b')
    result.current('c')

    vi.advanceTimersByTime(500)

    expect(fn).toHaveBeenCalledTimes(1)
    expect(fn).toHaveBeenCalledWith('c')
  })

  it('clears the pending timer on unmount', () => {
    const fn = vi.fn()
    const { result, unmount } = renderHook(() => useDebouncedCallback(fn, 500))

    result.current('a')
    unmount()
    vi.advanceTimersByTime(500)

    expect(fn).not.toHaveBeenCalled()
  })

  it('clears the pending timer when the delay changes', () => {
    const fn = vi.fn()
    const { result, rerender } = renderHook(({ delay }) => useDebouncedCallback(fn, delay), {
      initialProps: { delay: 500 },
    })

    result.current('a')
    rerender({ delay: 1000 })
    vi.advanceTimersByTime(500)

    expect(fn).not.toHaveBeenCalled()
  })
})
