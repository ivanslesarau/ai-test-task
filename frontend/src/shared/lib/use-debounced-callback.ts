import { useEffect, useMemo, useRef } from 'react'

/**
 * A typed debounced callback. Clears its pending timer on unmount and
 * whenever `delayMs` changes, so a stale timer from a previous delay never
 * fires after the component has moved on.
 *
 * No `any`, and no `NodeJS.Timeout` in the public signature — the timer
 * handle type is whatever `setTimeout` returns in this runtime, kept
 * entirely internal.
 */
export function useDebouncedCallback<TArgs extends unknown[]>(
  fn: (...args: TArgs) => void,
  delayMs: number,
): (...args: TArgs) => void {
  const fnRef = useRef(fn)
  fnRef.current = fn

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [delayMs])

  return useMemo(() => {
    return (...args: TArgs) => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current)
      }
      timerRef.current = setTimeout(() => {
        timerRef.current = null
        fnRef.current(...args)
      }, delayMs)
    }
  }, [delayMs])
}
