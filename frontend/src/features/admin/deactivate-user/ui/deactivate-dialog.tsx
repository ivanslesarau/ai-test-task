import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { useUiStore } from '@/app/store/ui-store'
import { userKeys } from '@/entities/user/api/query-keys'
import { useUserDetail } from '@/entities/user/api/use-users'
import { useDeactivateUser } from '@/entities/user/api/use-user-status'
import { isApiError } from '@/shared/api/errors'
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

/**
 * Renders itself only when the Zustand store's `pendingAction` names this
 * dialog and a userId — that id is the only thing read from the store;
 * the account itself always comes fresh from the query cache
 * (constitution Principle IV: no server data lives in Zustand).
 */
export function DeactivateDialog() {
  const pendingAction = useUiStore((state) => state.pendingAction)
  const clearPendingAction = useUiStore((state) => state.clearPendingAction)
  const isOpen = pendingAction?.kind === 'deactivate'
  const userId = pendingAction?.userId ?? ''

  const { data: user } = useUserDetail(userId)
  const deactivate = useDeactivateUser()
  const queryClient = useQueryClient()

  function handleConfirm() {
    if (!user) return
    deactivate.mutate(
      { userId, version: user.version },
      {
        onSuccess: () => {
          toast.success(`${user.first_name} ${user.last_name} was deactivated.`)
          clearPendingAction()
        },
        onError: (error) => {
          if (isApiError(error) && error.status === 409) {
            // Stale version: re-fetch rather than silently overwriting —
            // the dialog stays open so the admin sees the refreshed
            // state before deciding whether to retry.
            void queryClient.invalidateQueries({ queryKey: userKeys.detail(userId) })
            toast.error('This account changed since you opened this dialog. Review and retry.')
            return
          }
          toast.error(isApiError(error) ? error.message : 'Could not deactivate this account')
          clearPendingAction()
        },
      },
    )
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={(open) => !open && clearPendingAction()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Deactivate this user?</AlertDialogTitle>
          <AlertDialogDescription>
            User will not be able to log in. All historical data will be preserved for analytics
            and compliance. Continue?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction disabled={deactivate.isPending} onClick={handleConfirm}>
            {deactivate.isPending ? 'Deactivating…' : 'Deactivate'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
