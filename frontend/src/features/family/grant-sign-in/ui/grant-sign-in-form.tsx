import { revalidateLogic, useForm } from '@tanstack/react-form'
import { toast } from 'sonner'

import { useGrantChildSignIn } from '@/entities/player-profile/api/use-child-signin'
import { buildGrantChildSignInSchema } from '@/features/family/grant-sign-in/model/schema'
import type { GrantChildSignInValues } from '@/features/family/grant-sign-in/model/schema'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'
import type { ChildSignIn } from '@/shared/api/types'
import { Button } from '@/shared/ui/button'
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'

interface GrantSignInFormProps {
  profileId: string
  /** The signed-in parent's own email — refused client-side too (FR-129,
   * FR-004), so the common mistake is caught before a round trip. */
  ownEmail: string
  onSuccess: (result: ChildSignIn) => void
}

/**
 * `PUT /me/players/{profile_id}/sign-in` (US11, FR-129, FR-130). Grants a
 * child their own sign-in and issues a setup invitation. `invitation_sent`
 * is surfaced, not assumed true (FR-064, D-06's lesson) — a failed
 * delivery is reported plainly rather than as a success.
 */
export function GrantSignInForm({ profileId, ownEmail, onSuccess }: GrantSignInFormProps) {
  const grantSignIn = useGrantChildSignIn()
  const schema = buildGrantChildSignInSchema(ownEmail)

  const form = useForm({
    defaultValues: { email: '' } satisfies GrantChildSignInValues,
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: schema },
    onSubmit: ({ value }) => {
      grantSignIn.mutate(
        { profileId, body: { email: value.email } },
        {
          onSuccess: (result) => {
            if (result.invitation_sent) {
              toast.success(`A setup link was sent to ${result.email}`)
            } else {
              // FR-064: never reported as success when delivery failed.
              toast.error(
                `The sign-in was created, but the setup email to ${result.email} could not be sent`,
              )
            }
            form.reset()
            onSuccess(result)
          },
          onError: (error) => {
            form.setErrorMap({
              onServer: toServerErrorMap(error),
            } as unknown as Parameters<typeof form.setErrorMap>[0])
          },
        },
      )
    },
  })

  return (
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
            <FormLabel htmlFor={field.name}>Child&apos;s email</FormLabel>
            <Input
              id={field.name}
              type="email"
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(event) => field.handleChange(event.target.value)}
              placeholder="child@example.com"
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
            {isSubmitting ? 'Granting…' : 'Grant sign-in'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
