import { useForm } from '@tanstack/react-form'

import { useSetupPassword } from '@/features/auth/set-password/api/use-setup-password'
import { setPasswordSchema } from '@/features/auth/set-password/model/schema'
import { isApiError } from '@/shared/api/errors'
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
    validators: { onChange: setPasswordSchema },
    onSubmit: ({ value }) => {
      setup.mutate({ token, password: value.password }, { onSuccess })
    },
  })

  const topLevelError = setup.isError && isApiError(setup.error) ? setup.error.message : null
  const passwordFieldError =
    setup.isError && isApiError(setup.error) ? setup.error.fieldMessage('password') : null

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        void form.handleSubmit()
      }}
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
            <FormMessage>
              {field.state.meta.errors.map((e) => e?.message).join(', ') || passwordFieldError}
            </FormMessage>
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
            <FormMessage>{field.state.meta.errors.map((e) => e?.message).join(', ')}</FormMessage>
          </FormItem>
        )}
      </form.Field>

      {topLevelError && !passwordFieldError && <FormMessage>{topLevelError}</FormMessage>}

      <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
        {([canSubmit, isSubmitting]) => (
          <Button type="submit" disabled={!canSubmit || isSubmitting}>
            {isSubmitting ? 'Setting password…' : 'Set password'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
