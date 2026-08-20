import { useState } from 'react'
import { toast } from 'sonner'

import { useUiStore } from '@/app/store/ui-store'
import { useEraseUser } from '@/entities/user/api/use-erase-user'
import { useUserDetail } from '@/entities/user/api/use-users'
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
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'

/**
 * Renders when the store's pendingAction names 'erase'. Unlike the
 * deactivate/reactivate dialogs, this one carries local form state (the
 * reason) — still never server data, just the in-progress text of an
 * unsaved input, which is exactly the kind of transient UI state Zustand
 * is not needed for and a plain useState covers.
 */
export function EraseDialog() {
  const pendingAction = useUiStore((state) => state.pendingAction)
  const clearPendingAction = useUiStore((state) => state.clearPendingAction)
  const isOpen = pendingAction?.kind === 'erase'
  const userId = pendingAction?.userId ?? ''

  const [reason, setReason] = useState('')
  const { data: user } = useUserDetail(userId)
  const erase = useEraseUser()

  function handleOpenChange(open: boolean) {
    if (!open) {
      setReason('')
      clearPendingAction()
    }
  }

  function handleConfirm() {
    if (!user || !reason.trim()) return
    erase.mutate(
      { userId, version: user.version, reason: reason.trim() },
      {
        onSuccess: () => {
          toast.success(`${user.first_name} ${user.last_name}'s personal information was erased.`)
          setReason('')
          clearPendingAction()
        },
        onError: (error) => {
          toast.error(isApiError(error) ? error.message : 'Could not erase this account')
        },
      },
    )
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={handleOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Erase this user&apos;s personal information?</AlertDialogTitle>
          <AlertDialogDescription>
            Personal information will be removed. Historical records will show &quot;Deleted
            User&quot;. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <FormItem>
          <FormLabel htmlFor="erase-reason">Reason</FormLabel>
          <Input
            id="erase-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="e.g. GDPR erasure request"
          />
          <FormMessage>{!reason.trim() ? 'A reason is required.' : ''}</FormMessage>
        </FormItem>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            disabled={!reason.trim() || erase.isPending}
            onClick={handleConfirm}
          >
            {erase.isPending ? 'Erasing…' : 'Erase'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
