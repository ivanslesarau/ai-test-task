import { revalidateLogic, useForm } from '@tanstack/react-form'
import { toast } from 'sonner'

import { useUpdatePlayerProfile } from '@/entities/player-profile/api/use-update-player'
import { buildDefaultValues } from '@/features/family/edit-player/model/field-values'
import { playerProfileUpdateSchema } from '@/features/family/edit-player/model/schema'
import type { PlayerProfileUpdateValues } from '@/features/family/edit-player/model/schema'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'
import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'
import type { Gender, PlayerProfile } from '@/shared/api/types'
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

interface EditPlayerFormProps {
  profile: PlayerProfile
  onSuccess?: () => void
}

/**
 * `PATCH /me/players/{profile_id}` (US9, FR-107, FR-147, research.md
 * R-37). Which fields render is driven entirely by `profile.kind` — the
 * same "server-decided field set" shape `features/profile/edit-own`
 * uses, adapted from a role-keyed list to a kind-keyed one.
 */
export function EditPlayerForm({ profile, onSuccess }: EditPlayerFormProps) {
  const updateProfile = useUpdatePlayerProfile()
  const isChild = profile.kind === 'child'

  const form = useForm({
    defaultValues: buildDefaultValues(profile),
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: playerProfileUpdateSchema },
    onSubmit: ({ value }) => {
      const normalized = normalizeEmptyToNull(value) as PlayerProfileUpdateValues
      updateProfile.mutate(
        { profileId: profile.id, body: normalized },
        {
          onSuccess: () => {
            toast.success('Player updated')
            onSuccess?.()
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
      {isChild && (
        <div className="grid grid-cols-2 gap-4">
          <form.Field name="first_name">
            {(field) => (
              <FormItem>
                <FormLabel htmlFor={field.name}>First name</FormLabel>
                <Input
                  id={field.name}
                  value={String(field.state.value ?? '')}
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
                  value={String(field.state.value ?? '')}
                  onBlur={field.handleBlur}
                  onChange={(event) => field.handleChange(event.target.value)}
                />
                <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
              </FormItem>
            )}
          </form.Field>
        </div>
      )}

      <form.Field name="date_of_birth">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Date of birth</FormLabel>
            <Input
              id={field.name}
              type="date"
              value={String(field.state.value ?? '')}
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
              value={field.state.value ?? ''}
              onValueChange={(value) => field.handleChange(value as Gender)}
            >
              <SelectTrigger id={field.name}>
                <SelectValue placeholder="Select a gender" />
              </SelectTrigger>
              <SelectContent>
                {GENDER_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
          </FormItem>
        )}
      </form.Field>

      <div className="grid grid-cols-2 gap-4">
        <form.Field name="school">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>School</FormLabel>
              <Input
                id={field.name}
                value={String(field.state.value ?? '')}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
            </FormItem>
          )}
        </form.Field>

        <form.Field name="jersey_number">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>Jersey number</FormLabel>
              <Input
                id={field.name}
                value={String(field.state.value ?? '')}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
              />
              <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
            </FormItem>
          )}
        </form.Field>
      </div>

      {isChild && (
        <form.Field name="tokens_without_approval">
          {(field) => (
            <FormItem className="flex-row items-center gap-2">
              <Checkbox
                id={field.name}
                checked={Boolean(field.state.value)}
                onCheckedChange={(value) => field.handleChange(value === true)}
              />
              <FormLabel htmlFor={field.name}>Allow spending tokens without approval</FormLabel>
            </FormItem>
          )}
        </form.Field>
      )}

      <form.Subscribe selector={(state) => state.errors}>
        {(errors) => {
          const message = fieldErrorText(errors)
          return message ? <FormMessage>{message}</FormMessage> : null
        }}
      </form.Subscribe>

      <form.Subscribe selector={(state) => state.isSubmitting}>
        {(isSubmitting) => (
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Saving…' : 'Save changes'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
