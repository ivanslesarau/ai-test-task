import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { useUiStore } from '@/app/store/ui-store'
import { userKeys } from '@/entities/user/api/query-keys'
import { useUserDetail } from '@/entities/user/api/use-users'
import { useReactivateUser } from '@/entities/user/api/use-user-status'
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

export function ReactivateDialog() {
  const pendingAction = useUiStore((state) => state.pendingAction)
  const clearPendingAction = useUiStore((state) => state.clearPendingAction)
  const isOpen = pendingAction?.kind === 'reactivate'
  const userId = pendingAction?.userId ?? ''

  const { data: user } = useUserDetail(userId)
  const reactivate = useReactivateUser()
  const queryClient = useQueryClient()

  function handleConfirm() {
    if (!user) return
    reactivate.mutate(
      { userId, version: user.version },
      {
        onSuccess: () => {
          toast.success(`${user.first_name} ${user.last_name} was reactivated.`)
          clearPendingAction()
        },
        onError: (error) => {
          if (isApiError(error) && error.status === 409) {
            void queryClient.invalidateQueries({ queryKey: userKeys.detail(userId) })
            toast.error('This account changed since you opened this dialog. Review and retry.')
            return
          }
          toast.error(isApiError(error) ? error.message : 'Could not reactivate this account')
          clearPendingAction()
        },
      },
    )
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={(open) => !open && clearPendingAction()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Reactivate this user?</AlertDialogTitle>
          <AlertDialogDescription>
            The account will be able to log in again with its existing password.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction disabled={reactivate.isPending} onClick={handleConfirm}>
            {reactivate.isPending ? 'Reactivating…' : 'Reactivate'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
