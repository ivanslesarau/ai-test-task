import { revalidateLogic, useForm } from '@tanstack/react-form'

import { useRegisterThroughJoinLink } from '@/features/join/register/api/use-register'
import { joinRegistrationSchema } from '@/features/join/register/model/schema'
import type { Gender, JoinResult } from '@/shared/api/types'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'
import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'
import { Button } from '@/shared/ui/button'
import { Checkbox } from '@/shared/ui/checkbox'
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'

const GENDER_OPTIONS: { value: Gender; label: string }[] = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
  { value: 'prefer_not_to_say', label: 'Prefer not to say' },
]

interface JoinRegisterFormProps {
  code: string
  onSuccess: (result: JoinResult) => void
}

export function JoinRegisterForm({ code, onSuccess }: JoinRegisterFormProps) {
  const register = useRegisterThroughJoinLink(code)

  const form = useForm({
    defaultValues: {
      first_name: '',
      last_name: '',
      email: '',
      password: '',
      phone: '',
      is_self: true,
      player_name: '',
      date_of_birth: '',
      gender: 'prefer_not_to_say' as Gender,
    },
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: joinRegistrationSchema },
    onSubmit: ({ value }) => {
      const normalized = normalizeEmptyToNull(value)
      register.mutate(
        {
          first_name: normalized.first_name,
          last_name: normalized.last_name,
          email: normalized.email,
          password: normalized.password,
          phone: normalized.phone,
          is_self: normalized.is_self,
          // Null when the account holder is the player (FR-074) — never
          // an empty string, whether is_self is true or the field was
          // simply left blank.
          player_name: normalized.is_self ? null : normalized.player_name,
          date_of_birth: normalized.date_of_birth,
          gender: normalized.gender,
        },
        {
          onSuccess,
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
            <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
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
            <FormLabel htmlFor={field.name}>Phone</FormLabel>
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

      <form.Field name="is_self">
        {(field) => (
          <FormItem className="flex flex-row items-center gap-2">
            <Checkbox
              id={field.name}
              checked={!field.state.value}
              onCheckedChange={(checked) => field.handleChange(!checked)}
            />
            <FormLabel htmlFor={field.name} className="font-normal">
              I&apos;m registering a player who isn&apos;t me
            </FormLabel>
          </FormItem>
        )}
      </form.Field>

      <form.Subscribe selector={(state) => state.values.is_self}>
        {(isSelf) =>
          !isSelf && (
            <form.Field name="player_name">
              {(field) => (
                <FormItem>
                  <FormLabel htmlFor={field.name}>Player&apos;s name</FormLabel>
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

      <div className="grid grid-cols-2 gap-4">
        <form.Field name="date_of_birth">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>Date of birth</FormLabel>
              <Input
                id={field.name}
                type="date"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
            </FormItem>
          )}
        </form.Field>

        <form.Field name="gender">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>Gender</FormLabel>
              <Select
                value={field.state.value}
                onValueChange={(value) => field.handleChange(value as Gender)}
              >
                <SelectTrigger id={field.name}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {GENDER_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormItem>
          )}
        </form.Field>
      </div>

      <form.Subscribe selector={(state) => state.errors}>
        {(errors) => {
          const message = fieldErrorText(errors)
          return message ? <FormMessage>{message}</FormMessage> : null
        }}
      </form.Subscribe>

      <form.Subscribe selector={(state) => state.isSubmitting}>
        {(isSubmitting) => (
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Joining…' : 'Join'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
