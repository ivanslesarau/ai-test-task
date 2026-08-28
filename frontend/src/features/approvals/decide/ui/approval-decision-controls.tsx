import { useState } from 'react'

import { revalidateLogic, useForm } from '@tanstack/react-form'
import { toast } from 'sonner'

import {
  useApproveApproval,
  useDenyApproval,
  useRequestInfoOnApproval,
} from '@/entities/approval/api/use-resolve-approval'
import {
  approvalDecisionSchema,
  approvalInfoSchema,
} from '@/features/approvals/decide/model/schema'
import { isApiError } from '@/shared/api/errors'
import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'
import { Button } from '@/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'

type OpenDialog = 'approve' | 'deny' | 'request-info' | null

interface ApprovalDecisionControlsProps {
  requestId: string
  childDisplayName: string
}

/**
 * Approve, deny, and request-info controls for one row of the parent's
 * decision queue (US12, tasks.md T407, T408). Each can carry a note,
 * routed through `normalizeEmptyToNull` so an opened-but-empty note box
 * sends `null` (contracts/frontend-contracts.md §17).
 *
 * `request_already_resolved` (409) is an **ordinary outcome**, not an
 * error state: a client whose own countdown still shows time remaining
 * can legitimately lose the race (research.md R-41), so every mutation
 * here treats it as "someone else already decided" rather than a
 * failure toast.
 */
export function ApprovalDecisionControls({
  requestId,
  childDisplayName,
}: ApprovalDecisionControlsProps) {
  const [openDialog, setOpenDialog] = useState<OpenDialog>(null)
  const approve = useApproveApproval()
  const deny = useDenyApproval()
  const requestInfo = useRequestInfoOnApproval()

  function handleAlreadyResolved(error: unknown): boolean {
    if (isApiError(error) && error.code === 'request_already_resolved') {
      toast.info(`That request for ${childDisplayName} was already decided.`)
      setOpenDialog(null)
      return true
    }
    return false
  }

  function handleApprove() {
    approve.mutate(
      { requestId, note: null },
      {
        onSuccess: () => toast.success(`Approved — ${childDisplayName} is now connected.`),
        onError: (error) => {
          if (!handleAlreadyResolved(error)) {
            toast.error(isApiError(error) ? error.message : 'Could not approve this request')
          }
        },
      },
    )
  }

  const denyForm = useForm({
    defaultValues: { note: '' },
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: approvalDecisionSchema },
    onSubmit: ({ value }) => {
      const normalized = normalizeEmptyToNull(value)
      deny.mutate(
        { requestId, note: normalized.note },
        {
          onSuccess: () => {
            toast.success('Denied')
            denyForm.reset()
            setOpenDialog(null)
          },
          onError: (error) => {
            if (!handleAlreadyResolved(error)) {
              toast.error(isApiError(error) ? error.message : 'Could not deny this request')
            }
          },
        },
      )
    },
  })

  const infoForm = useForm({
    defaultValues: { note: '' },
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: approvalInfoSchema },
    onSubmit: ({ value }) => {
      requestInfo.mutate(
        { requestId, note: value.note.trim() },
        {
          onSuccess: () => {
            toast.success('Asked for more information')
            infoForm.reset()
            setOpenDialog(null)
          },
          onError: (error) => {
            if (!handleAlreadyResolved(error)) {
              toast.error(isApiError(error) ? error.message : 'Could not send that request')
            }
          },
        },
      )
    },
  })

  return (
    <div className="flex gap-2">
      <Button size="sm" onClick={handleApprove} disabled={approve.isPending}>
        {approve.isPending ? 'Approving…' : 'Approve'}
      </Button>
      <Button size="sm" variant="outline" onClick={() => setOpenDialog('deny')}>
        Deny
      </Button>
      <Button size="sm" variant="outline" onClick={() => setOpenDialog('request-info')}>
        Ask a question
      </Button>

      <Dialog open={openDialog === 'deny'} onOpenChange={(open) => !open && setOpenDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deny this request?</DialogTitle>
            <DialogDescription>
              {childDisplayName} will see that it was denied, along with any note you add.
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              void denyForm.handleSubmit()
            }}
            noValidate
            className="flex flex-col gap-4"
          >
            <denyForm.Field name="note">
              {(field) => (
                <FormItem>
                  <FormLabel htmlFor={field.name}>Note (optional)</FormLabel>
                  <Input
                    id={field.name}
                    value={field.state.value}
                    onBlur={field.handleBlur}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                  <FormMessage>{field.state.meta.errors.map(String).join(', ')}</FormMessage>
                </FormItem>
              )}
            </denyForm.Field>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpenDialog(null)}>
                Cancel
              </Button>
              <Button type="submit" variant="destructive" disabled={deny.isPending}>
                {deny.isPending ? 'Denying…' : 'Deny'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog
        open={openDialog === 'request-info'}
        onOpenChange={(open) => !open && setOpenDialog(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ask {childDisplayName} a question</DialogTitle>
            <DialogDescription>
              The request stays open — the deadline does not restart while you wait for a reply.
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              void infoForm.handleSubmit()
            }}
            noValidate
            className="flex flex-col gap-4"
          >
            <infoForm.Field name="note">
              {(field) => (
                <FormItem>
                  <FormLabel htmlFor={field.name}>Your question</FormLabel>
                  <Input
                    id={field.name}
                    value={field.state.value}
                    onBlur={field.handleBlur}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                  <FormMessage>{field.state.meta.errors.map(String).join(', ')}</FormMessage>
                </FormItem>
              )}
            </infoForm.Field>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpenDialog(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={requestInfo.isPending}>
                {requestInfo.isPending ? 'Sending…' : 'Send'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
