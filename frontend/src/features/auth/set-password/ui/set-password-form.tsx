import { revalidateLogic, useForm } from '@tanstack/react-form'

import { useSetupPassword } from '@/features/auth/set-password/api/use-setup-password'
import { setPasswordSchema } from '@/features/auth/set-password/model/schema'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'
import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'
import { Button } from '@/shared/ui/button'
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'

interface SetPasswordFormProps {
  token: string
  onSuccess: () => void
}

export function SetPasswordForm({ token, onSuccess }: SetPasswordFormProps) {
  const setup = useSetupPassword()

  const form = useForm({
    defaultValues: { password: '', confirmPassword: '' },
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: setPasswordSchema },
    onSubmit: ({ value }) => {
      // `password` is required and non-empty by the time Zod lets
      // submission through, so this is a no-op in practice — it still
      // runs, because Principle VI requires every submit handler to
      // route through the one shared normalizer.
      const normalized = normalizeEmptyToNull(value)
      setup.mutate(
        { token, password: normalized.password },
        {
          onSuccess,
          onError: (error) => {
            // Breached-password membership and password-policy failures
            // both attribute to "password" from the server; routing them
            // through the shared helper means this form needs no
            // one-off `fieldMessage('password')` call of its own. The
            // `onServer` slot is only typed once `useForm`'s dedicated
            // type parameter is threaded through — nothing else about
            // this form needs that, so the cast is scoped to this one
            // call, against the setter's own parameter type.
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
      // The browser's own constraint validation (e.g. for type="email")
      // can block the submit event before React sees it once nothing
      // validates on every keystroke; the Zod schema is the one source
      // of truth for what renders (FR-057, FR-058).
      noValidate
      className="flex flex-col gap-4"
    >
      <form.Field name="password">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>New password</FormLabel>
            <Input
              id={field.name}
              type="password"
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(event) => field.handleChange(event.target.value)}
            />
            <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
          </FormItem>
        )}
      </form.Field>

      <form.Field name="confirmPassword">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Confirm password</FormLabel>
            <Input
              id={field.name}
              type="password"
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(event) => field.handleChange(event.target.value)}
            />
            <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
          </FormItem>
        )}
      </form.Field>

      {/* The form-level message — including the `onServer` message
          `toServerErrorMap` produces when a 422 carries no `fields` —
          lands in `state.errors` alongside every other validation cause,
          so reading it through the same `fieldErrorText` helper needs no
          separate, unwrap-generic-dependent selector. */}
      <form.Subscribe selector={(state) => state.errors}>
        {(errors) => {
          const message = fieldErrorText(errors)
          return message ? <FormMessage>{message}</FormMessage> : null
        }}
      </form.Subscribe>

      <form.Subscribe selector={(state) => state.isSubmitting}>
        {(isSubmitting) => (
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Setting password…' : 'Set password'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
