import { ChevronLeft } from 'lucide-react'
import type { LinkProps } from '@tanstack/react-router'
import { useCanGoBack, useRouter } from '@tanstack/react-router'

import { Button } from '@/shared/ui/button'

interface BackButtonProps {
  /**
   * Required, not optional: a deep-linked page has no browser history to
   * go back to, so it must always have somewhere to send the visitor
   * (contracts/frontend-contracts.md §7.3). Typed through `LinkProps['to']`
   * so no route is ever built by string concatenation (Principle IV).
   */
  fallbackTo: LinkProps['to']
  className?: string
}

/**
 * `history.back()` when there is history to go back to, otherwise
 * navigates to the required `fallbackTo` route. History-based back is what
 * restores a filtered directory view without threading search params
 * through every link (FR-061).
 */
export function BackButton({ fallbackTo, className }: BackButtonProps) {
  const router = useRouter()
  const canGoBack = useCanGoBack()

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      className={className}
      onClick={() => {
        if (canGoBack) {
          router.history.back()
        } else {
          void router.navigate({ to: fallbackTo })
        }
      }}
    >
      <ChevronLeft />
      Back
    </Button>
  )
}
