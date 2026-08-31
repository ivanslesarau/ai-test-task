import { useEffect, useState } from 'react'

import { toast } from 'sonner'

import { useEndImpersonation } from '@/entities/impersonation/api/use-end-impersonation'
import { useSession } from '@/entities/session/api/use-session'
import { isApiError } from '@/shared/api/errors'
import { Button } from '@/shared/ui/button'

function formatRemaining(expiresAt: string): string {
  const remainingMs = new Date(expiresAt).getTime() - Date.now()
  if (remainingMs <= 0) return '0:00'
  const totalSeconds = Math.floor(remainingMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

/**
 * Persistent, on every authenticated view (FR-044). Driven purely by
 * `session.impersonation` being non-null — no client-side inference from
 * a role mismatch, no local timer that ends anything (frontend-contracts.md
 * §35, §38). The countdown is display-only: when it reaches zero, nothing
 * happens here — only the server, on the next request, actually ends the
 * impersonation (FR-046, research.md R2-19).
 */
export function ImpersonationBanner() {
  const { data: session } = useSession()
  const endImpersonation = useEndImpersonation()
  const impersonation = session?.impersonation ?? null

  const [, forceTick] = useState(0)
  useEffect(() => {
    if (!impersonation) return
    const interval = setInterval(() => forceTick((n) => n + 1), 1000)
    return () => clearInterval(interval)
  }, [impersonation])

  if (!impersonation) return null

  function handleExit() {
    endImpersonation.mutate(undefined, {
      onError: (error) => {
        toast.error(isApiError(error) ? error.message : 'Could not exit impersonation.')
      },
    })
  }

  return (
    <div
      role="status"
      className="flex w-full items-center justify-between gap-4 bg-destructive px-4 py-2 text-body text-white"
    >
      <p>
        Viewing as <strong>{impersonation.target.display_name}</strong> — impersonated by{' '}
        <strong>{impersonation.admin.display_name}</strong>. Time remaining:{' '}
        {formatRemaining(impersonation.expires_at)}
      </p>
      <Button
        variant="outline"
        size="sm"
        className="border-white text-white hover:bg-white/10 hover:text-white"
        disabled={endImpersonation.isPending}
        onClick={handleExit}
      >
        {endImpersonation.isPending ? 'Exiting…' : 'Exit'}
      </Button>
    </div>
  )
}
