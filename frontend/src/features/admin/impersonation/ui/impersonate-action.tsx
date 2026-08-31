import { useUiStore } from '@/app/store/ui-store'
import { useSession } from '@/entities/session/api/use-session'
import type { UserSummary } from '@/shared/api/types'
import { Button } from '@/shared/ui/button'

interface ImpersonateActionProps {
  user: UserSummary
}

/**
 * The user-directory row action that starts an impersonation (FR-040).
 * Withheld for a Super Admin row (FR-042's structural refusal has nothing
 * to refuse if the control is never offered), the caller's own row (no
 * self-impersonation), and an already-erased account — each of these is
 * also refused on the request by the server; withholding the control
 * here is a convenience, never the security boundary.
 */
export function ImpersonateAction({ user }: ImpersonateActionProps) {
  const { data: session } = useSession()
  const openPendingAction = useUiStore((state) => state.openPendingAction)

  if (user.role === 'super_admin') return null
  if (user.status === 'deleted') return null
  if (session && session.id === user.id) return null

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => openPendingAction({ kind: 'impersonate', userId: user.id })}
    >
      Impersonate
    </Button>
  )
}
