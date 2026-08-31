import { toast } from 'sonner'

import { useUiStore } from '@/app/store/ui-store'
import { useStartImpersonation } from '@/entities/impersonation/api/use-start-impersonation'
import { useUserDetail } from '@/entities/user/api/use-users'
import { isApiError } from '@/shared/api/errors'
import type { UserRole } from '@/shared/api/types'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/shared/ui/alert-dialog'

const ROLE_LABEL: Record<UserRole, string> = {
  super_admin: 'Super Admin',
  trainer: 'Trainer',
  coach: 'Coach',
  player_parent: 'Player/Parent',
}

/**
 * Names the person and their role before starting an impersonation
 * (FR-040). Renders only when the Zustand store's `pendingAction` names
 * this dialog and a userId — the account itself always comes fresh from
 * the query cache, never copied into the store (constitution Principle
 * IV), exactly like `DeactivateDialog`.
 */
export function ImpersonationConfirmDialog() {
  const pendingAction = useUiStore((state) => state.pendingAction)
  const clearPendingAction = useUiStore((state) => state.clearPendingAction)
  const isOpen = pendingAction?.kind === 'impersonate'
  const userId = pendingAction?.userId ?? ''

  const { data: user } = useUserDetail(userId)
  const startImpersonation = useStartImpersonation()

  function handleConfirm() {
    if (!user) return
    startImpersonation.mutate(
      { user_id: userId },
      {
        onError: (error) => {
          toast.error(isApiError(error) ? error.message : 'Could not start impersonation.')
          clearPendingAction()
        },
      },
    )
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={(open) => !open && clearPendingAction()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            View the platform as {user ? `${user.first_name} ${user.last_name}` : 'this person'}?
          </AlertDialogTitle>
          <AlertDialogDescription>
            {user && (
              <>
                You will see and be able to do exactly what this {ROLE_LABEL[user.role]} can, for
                up to one hour, under a visible banner naming you as the acting Super Admin. Every
                change you make will be recorded against both accounts.
              </>
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction disabled={startImpersonation.isPending} onClick={handleConfirm}>
            {startImpersonation.isPending ? 'Starting…' : 'Start impersonating'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
