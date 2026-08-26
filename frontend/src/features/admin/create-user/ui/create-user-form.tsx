import { revalidateLogic, useForm } from '@tanstack/react-form'

import { useCreateUser } from '@/entities/user/api/use-users'
import { createUserSchema } from '@/features/admin/create-user/model/schema'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'
import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'
import type { CreatedUser, UserRole } from '@/shared/api/types'
import { Button } from '@/shared/ui/button'
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'

const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: 'trainer', label: 'Trainer' },
  { value: 'coach', label: 'Coach' },
  { value: 'player_parent', label: 'Player/Parent' },
  { value: 'super_admin', label: 'Super Admin' },
]

interface CreateUserFormProps {
  onSuccess: (result: CreatedUser) => void
}

export function CreateUserForm({ onSuccess }: CreateUserFormProps) {
  const createUser = useCreateUser()

  const form = useForm({
    defaultValues: {
      role: 'trainer' as UserRole,
      email: '',
      first_name: '',
      last_name: '',
      phone: '',
      business_name: '',
    },
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: createUserSchema },
    onSubmit: ({ value }) => {
      const normalized = normalizeEmptyToNull(value)
      createUser.mutate(
        {
          role: normalized.role,
          email: normalized.email,
          first_name: normalized.first_name,
          last_name: normalized.last_name,
          phone: normalized.phone,
          ...(normalized.role === 'trainer' ? { business_name: normalized.business_name } : {}),
        },
        {
          onSuccess,
          onError: (error) => {
            // The `onServer` slot's type is only known once `useForm`'s
            // dedicated type parameter is threaded through — nothing
            // else about this form needs that, so the cast is scoped to
            // this one call, against the setter's own parameter type.
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
      <form.Field name="role">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Role</FormLabel>
            <Select
              value={field.state.value}
              onValueChange={(value) => field.handleChange(value as UserRole)}
            >
              <SelectTrigger id={field.name}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormItem>
        )}
      </form.Field>

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

      <div className="grid grid-cols-2 gap-4">
        <form.Field name="first_name">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>First name</FormLabel>
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

        <form.Field name="last_name">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>Last name</FormLabel>
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
      </div>

      <form.Field name="phone">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Phone</FormLabel>
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

      <form.Subscribe selector={(state) => state.values.role}>
        {(role) =>
          role === 'trainer' && (
            <form.Field name="business_name">
              {(field) => (
                <FormItem>
                  <FormLabel htmlFor={field.name}>Business name</FormLabel>
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
          )
        }
      </form.Subscribe>

      <form.Subscribe selector={(state) => state.errors}>
        {(errors) => {
          const message = fieldErrorText(errors)
          return message ? <FormMessage>{message}</FormMessage> : null
        }}
      </form.Subscribe>

      <form.Subscribe selector={(state) => state.isSubmitting}>
        {(isSubmitting) => (
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating…' : 'Create user'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
