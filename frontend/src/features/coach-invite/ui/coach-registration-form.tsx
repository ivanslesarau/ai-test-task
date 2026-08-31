import { revalidateLogic, useForm } from '@tanstack/react-form'
import { toast } from 'sonner'

import { useRegisterThroughCoachInvitation } from '@/entities/coach-invitation/api/use-register-through-coach-invitation'
import { coachRegistrationSchema } from '@/features/coach-invite/model/registration-schema'
import { isApiError } from '@/shared/api/errors'
import type { CoachJoinResult } from '@/shared/api/types'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'
import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'
import { Button } from '@/shared/ui/button'
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'

interface CoachRegistrationFormProps {
  token: string
  invitedEmail: string
  onSuccess: (result: CoachJoinResult) => void
}

/**
 * No email, role, or trainer input anywhere on this form — the invited
 * address is shown read-only, taken straight from the preview response,
 * never collected from the visitor (FR-011, FR-013).
 */
export function CoachRegistrationForm({
  token,
  invitedEmail,
  onSuccess,
}: CoachRegistrationFormProps) {
  const register = useRegisterThroughCoachInvitation(token)

  const form = useForm({
    defaultValues: {
      first_name: '',
      last_name: '',
      password: '',
      phone: '',
      bio: '',
      credentials: '',
      certifications: '',
    },
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: coachRegistrationSchema },
    onSubmit: ({ value }) => {
      const normalized = normalizeEmptyToNull(value)
      register.mutate(normalized, {
        onSuccess,
        onError: (error) => {
          form.setErrorMap({
            onServer: toServerErrorMap(error),
          } as unknown as Parameters<typeof form.setErrorMap>[0])
          if (!isApiError(error) || error.fields.length === 0) {
            toast.error(isApiError(error) ? error.message : 'Could not create your account')
          }
        },
      })
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
      <FormItem>
        <FormLabel htmlFor="invited-email">Email</FormLabel>
        <Input id="invited-email" value={invitedEmail} disabled readOnly />
      </FormItem>

      <div className="grid grid-cols-2 gap-4">
        <form.Field name="first_name">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>First name</FormLabel>
              <Input
                id={field.name}
                autoComplete="given-name"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
            </FormItem>
          )}
        </form.Field>

        <form.Field name="last_name">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>Last name</FormLabel>
              <Input
                id={field.name}
                autoComplete="family-name"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
            </FormItem>
          )}
        </form.Field>
      </div>

      <form.Field name="password">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Password</FormLabel>
            <Input
              id={field.name}
              type="password"
              autoComplete="new-password"
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(event) => field.handleChange(event.target.value)}
            />
            <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
          </FormItem>
        )}
      </form.Field>

      <form.Field name="phone">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Phone (optional)</FormLabel>
            <Input
              id={field.name}
              type="tel"
              autoComplete="tel"
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(event) => field.handleChange(event.target.value)}
            />
            <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
          </FormItem>
        )}
      </form.Field>

      <form.Field name="bio">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Bio (optional)</FormLabel>
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

      <form.Field name="credentials">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Credentials (optional)</FormLabel>
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

      <form.Field name="certifications">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Certifications (optional)</FormLabel>
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
            {isSubmitting ? 'Creating account…' : 'Create account and join'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
