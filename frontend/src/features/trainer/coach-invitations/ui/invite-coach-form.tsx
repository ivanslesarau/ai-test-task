import { useState } from 'react'

import { revalidateLogic, useForm } from '@tanstack/react-form'
import { toast } from 'sonner'

import { useIssueCoachInvitation } from '@/entities/coach-invitation/api/use-issue-coach-invitation'
import { useResendCoachInvitation } from '@/entities/coach-invitation/api/use-resend-coach-invitation'
import { useRevokeCoachInvitation } from '@/entities/coach-invitation/api/use-revoke-coach-invitation'
import { coachInvitationCreateSchema } from '@/entities/coach-invitation/model/invitation'
import type { CoachInvitationCreateValues } from '@/entities/coach-invitation/model/invitation'
import { getPendingInvitation } from '@/features/trainer/coach-invitations/model/pending-conflict'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'
import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'
import type { CoachInvitation, CoachInvitationCreate } from '@/shared/api/types'
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
import { Button } from '@/shared/ui/button'
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'

const DEFAULT_VALUES: CoachInvitationCreateValues = { email: '', invitee_name: '', message: '' }

/**
 * `POST /trainer/coach-invitations` (FR-001 – FR-003, FR-007, FR-008,
 * FR-010). Routed through `normalizeEmptyToNull` before the request body
 * is built (Principle VI) — no inline ternary at this call site. A 409
 * `coach_invitation_pending` is rendered as an offer to resend or revoke
 * the existing invitation, never as an ordinary field error (FR-007).
 */
export function InviteCoachForm() {
  const issueInvitation = useIssueCoachInvitation()
  const resendInvitation = useResendCoachInvitation()
  const revokeInvitation = useRevokeCoachInvitation()
  const [pending, setPending] = useState<CoachInvitation | null>(null)

  const form = useForm({
    defaultValues: DEFAULT_VALUES,
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: coachInvitationCreateSchema },
    onSubmit: ({ value }) => {
      const normalized = normalizeEmptyToNull(value)
      const body: CoachInvitationCreate = {
        email: normalized.email,
        invitee_name: normalized.invitee_name,
        message: normalized.message,
      }
      issueInvitation.mutate(body, {
        onSuccess: () => {
          toast.success('Invitation sent.')
          form.reset()
        },
        onError: (error) => {
          const existing = getPendingInvitation(error)
          if (existing) {
            setPending(existing)
            return
          }
          form.setErrorMap({
            onServer: toServerErrorMap(error),
          } as unknown as Parameters<typeof form.setErrorMap>[0])
        },
      })
    },
  })

  return (
    <>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          void form.handleSubmit()
        }}
        noValidate
        className="flex flex-col gap-4"
      >
        <form.Field name="email">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>Email</FormLabel>
              <Input
                id={field.name}
                type="email"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
            </FormItem>
          )}
        </form.Field>

        <form.Field name="invitee_name">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>Name (optional)</FormLabel>
              <Input
                id={field.name}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
            </FormItem>
          )}
        </form.Field>

        <form.Field name="message">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>Personal message (optional)</FormLabel>
              <Input
                id={field.name}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
            </FormItem>
          )}
        </form.Field>

        <form.Subscribe selector={(state) => state.errors}>
          {(errors) => {
            const message = fieldErrorText(errors)
            return message ? <FormMessage>{message}</FormMessage> : null
          }}
        </form.Subscribe>

        <form.Subscribe selector={(state) => state.isSubmitting}>
          {(isSubmitting) => (
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Sending…' : 'Invite coach'}
            </Button>
          )}
        </form.Subscribe>
      </form>

      {pending && (
        <AlertDialog open onOpenChange={(open) => !open && setPending(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>An invitation is already awaiting a response</AlertDialogTitle>
              <AlertDialogDescription>
                {pending.invited_email} already has an invitation from you, sent{' '}
                {new Date(pending.issued_at).toLocaleDateString()}. Resend it to replace the
                link, or revoke it to withdraw it.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => setPending(null)}>Cancel</AlertDialogCancel>
              <Button
                type="button"
                variant="outline"
                disabled={revokeInvitation.isPending}
                onClick={() => {
                  revokeInvitation.mutate(pending.id, {
                    onSuccess: () => {
                      toast.success('Invitation revoked.')
                      setPending(null)
                    },
                  })
                }}
              >
                Revoke
              </Button>
              <AlertDialogAction
                disabled={resendInvitation.isPending}
                onClick={() => {
                  resendInvitation.mutate(pending.id, {
                    onSuccess: () => {
                      toast.success('Invitation resent.')
                      setPending(null)
                      form.reset()
                    },
                  })
                }}
              >
                Resend
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </>
  )
}
