import { useForm } from '@tanstack/react-form'

import { useSignIn } from '@/features/auth/sign-in/api/use-sign-in'
import { signInSchema } from '@/features/auth/sign-in/model/schema'
import { isApiError } from '@/shared/api/errors'
import type { CurrentUser } from '@/shared/api/types'
import { Button } from '@/shared/ui/button'
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'

interface SignInFormProps {
  onSuccess: (user: CurrentUser) => void
}

export function SignInForm({ onSuccess }: SignInFormProps) {
  const signIn = useSignIn()

  const form = useForm({
    defaultValues: { email: '', password: '' },
    validators: { onChange: signInSchema },
    onSubmit: ({ value }) => {
      // mutate() rather than mutateAsync(): the failure path is already
      // fully handled through signIn.isError/signIn.error below, so
      // nothing here needs to await or catch a rejected promise.
      signIn.mutate(value, { onSuccess })
    },
  })

  const topLevelError =
    signIn.isError && isApiError(signIn.error) ? signIn.error.message : null

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        void form.handleSubmit()
      }}
      className="flex flex-col gap-4"
    >
      <form.Field name="email">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Email</FormLabel>
            <Input
              id={field.name}
              type="email"
              autoComplete="email"
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(event) => field.handleChange(event.target.value)}
            />
            <FormMessage>{field.state.meta.errors.map((e) => e?.message).join(', ')}</FormMessage>
          </FormItem>
        )}
      </form.Field>

      <form.Field name="password">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Password</FormLabel>
            <Input
              id={field.name}
              type="password"
              autoComplete="current-password"
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(event) => field.handleChange(event.target.value)}
            />
            <FormMessage>{field.state.meta.errors.map((e) => e?.message).join(', ')}</FormMessage>
          </FormItem>
        )}
      </form.Field>

      {topLevelError && <FormMessage>{topLevelError}</FormMessage>}

      <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
        {([canSubmit, isSubmitting]) => (
          <Button type="submit" disabled={!canSubmit || isSubmitting}>
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
