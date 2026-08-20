import { useForm } from '@tanstack/react-form'
import { toast } from 'sonner'

import { useUpdateOwnProfile } from '@/entities/user/api/use-own-profile'
import { FIELD_CONFIG } from '@/features/profile/edit-own/model/field-config'
import { buildDefaultValues } from '@/features/profile/edit-own/model/field-values'
import { ownProfileUpdateSchema } from '@/features/profile/edit-own/model/schema'
import type { OwnProfileUpdateValues } from '@/features/profile/edit-own/model/schema'
import { isApiError } from '@/shared/api/errors'
import type { OwnProfile } from '@/shared/api/types'
import { Button } from '@/shared/ui/button'
import { Checkbox } from '@/shared/ui/checkbox'
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'

interface EditProfileFormProps {
  profile: OwnProfile
}

/**
 * Which fields render — and which of them are even present in the
 * submitted payload — is driven entirely by `profile.editable_fields`,
 * the server's own answer to "what may this role change" (FR-031,
 * FR-033). This form never hardcodes a per-role field list.
 */
export function EditProfileForm({ profile }: EditProfileFormProps) {
  const updateProfile = useUpdateOwnProfile()

  const form = useForm({
    defaultValues: buildDefaultValues(profile),
    validators: { onChange: ownProfileUpdateSchema },
    onSubmit: ({ value }) => {
      updateProfile.mutate(value, {
        onSuccess: () => toast.success('Profile updated'),
        onError: (error) => {
          if (!isApiError(error) || error.fields.length === 0) {
            toast.error(isApiError(error) ? error.message : 'Could not update your profile')
          }
        },
      })
    },
  })

  const topLevelError =
    updateProfile.isError && isApiError(updateProfile.error) && updateProfile.error.fields.length === 0
      ? updateProfile.error.message
      : null

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        void form.handleSubmit()
      }}
      className="flex flex-col gap-4"
    >
      {(profile.editable_fields as (keyof OwnProfileUpdateValues)[]).map((fieldName) => {
        const config = FIELD_CONFIG[fieldName]
        if (!config) return null

        return (
          <form.Field key={fieldName} name={fieldName}>
            {(field) => {
              if (config.kind === 'checkbox') {
                const checked = Boolean(field.state.value)
                return (
                  <FormItem className="flex-row items-center gap-2">
                    <Checkbox
                      id={fieldName}
                      checked={checked}
                      onCheckedChange={(value) => field.handleChange(value === true)}
                    />
                    <FormLabel htmlFor={fieldName}>{config.label}</FormLabel>
                  </FormItem>
                )
              }

              return (
                <FormItem>
                  <FormLabel htmlFor={fieldName}>{config.label}</FormLabel>
                  <Input
                    id={fieldName}
                    value={String(field.state.value ?? '')}
                    onBlur={field.handleBlur}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                  <FormMessage>
                    {field.state.meta.errors.map((e) => e?.message).join(', ')}
                  </FormMessage>
                </FormItem>
              )
            }}
          </form.Field>
        )
      })}

      {topLevelError && <FormMessage>{topLevelError}</FormMessage>}

      <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
        {([canSubmit, isSubmitting]) => (
          <Button type="submit" disabled={!canSubmit || isSubmitting}>
            {isSubmitting ? 'Saving…' : 'Save changes'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
