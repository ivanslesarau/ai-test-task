import { useForm } from '@tanstack/react-form'

import { useCreateUser } from '@/entities/user/api/use-users'
import { createUserSchema } from '@/features/admin/create-user/model/schema'
import { isApiError } from '@/shared/api/errors'
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
    validators: { onChange: createUserSchema },
    onSubmit: ({ value }) => {
      createUser.mutate(
        {
          role: value.role,
          email: value.email,
          first_name: value.first_name,
          last_name: value.last_name,
          phone: value.phone,
          ...(value.role === 'trainer' ? { business_name: value.business_name } : {}),
        },
        { onSuccess },
      )
    },
  })

  const topLevelError =
    createUser.isError && isApiError(createUser.error) ? createUser.error.message : null

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        void form.handleSubmit()
      }}
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
            <FormMessage>{field.state.meta.errors.map((e) => e?.message).join(', ')}</FormMessage>
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
              <FormMessage>
                {field.state.meta.errors.map((e) => e?.message).join(', ')}
              </FormMessage>
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
              <FormMessage>
                {field.state.meta.errors.map((e) => e?.message).join(', ')}
              </FormMessage>
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
            <FormMessage>{field.state.meta.errors.map((e) => e?.message).join(', ')}</FormMessage>
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
                  <FormMessage>
                    {field.state.meta.errors.map((e) => e?.message).join(', ')}
                  </FormMessage>
                </FormItem>
              )}
            </form.Field>
          )
        }
      </form.Subscribe>

      {topLevelError && <FormMessage>{topLevelError}</FormMessage>}

      <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
        {([canSubmit, isSubmitting]) => (
          <Button type="submit" disabled={!canSubmit || isSubmitting}>
            {isSubmitting ? 'Creating…' : 'Create user'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
