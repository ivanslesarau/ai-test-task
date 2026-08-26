import { revalidateLogic, useForm } from '@tanstack/react-form'
import { toast } from 'sonner'

import { useUpdateOwnProfile } from '@/entities/user/api/use-own-profile'
import { FIELD_CONFIG } from '@/features/profile/edit-own/model/field-config'
import { buildDefaultValues } from '@/features/profile/edit-own/model/field-values'
import { ownProfileUpdateSchema } from '@/features/profile/edit-own/model/schema'
import type { OwnProfileUpdateValues } from '@/features/profile/edit-own/model/schema'
import { isApiError } from '@/shared/api/errors'
import type { OwnProfile } from '@/shared/api/types'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'
import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'
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
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: ownProfileUpdateSchema },
    onSubmit: ({ value }) => {
      // An untouched optional field defaults to '' from the controlled
      // input; normalizeEmptyToNull is what lets a cleared field actually
      // clear the column instead of writing '' (constitution Principle VI).
      updateProfile.mutate(normalizeEmptyToNull(value), {
        onSuccess: () => toast.success('Profile updated'),
        onError: (error) => {
          // The `onServer` slot's type is only known once `useForm`'s
          // dedicated type parameter is threaded through — nothing else
          // about this form needs that, so the cast is scoped to this
          // one call, against the setter's own parameter type.
          form.setErrorMap({
            onServer: toServerErrorMap(error),
          } as unknown as Parameters<typeof form.setErrorMap>[0])
          if (!isApiError(error) || error.fields.length === 0) {
            toast.error(isApiError(error) ? error.message : 'Could not update your profile')
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
      // The browser's own constraint validation (e.g. for type="email")
      // can block the submit event before React sees it once nothing
      // validates on every keystroke; the Zod schema is the one source
      // of truth for what renders (FR-057, FR-058).
      noValidate
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
                  <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
                </FormItem>
              )
            }}
          </form.Field>
        )
      })}

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
