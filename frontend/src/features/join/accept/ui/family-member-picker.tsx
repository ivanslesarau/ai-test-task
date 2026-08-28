import { revalidateLogic, useForm } from '@tanstack/react-form'

import { joinAcceptSchema } from '@/features/join/accept/model/schema'
import type { JoinAcceptRequest, JoinSelectableProfile } from '@/shared/api/types'
import { Button } from '@/shared/ui/button'
import { Checkbox } from '@/shared/ui/checkbox'

interface FamilyMemberPickerProps {
  trainerName: string
  selectableProfiles: JoinSelectableProfile[]
  onSubmit: (body: JoinAcceptRequest) => void
  isPending: boolean
}

/**
 * The "who will train with this trainer?" question (US13, FR-122,
 * Story 13). Already-associated profiles render as connected and
 * unselectable — selecting one again would cost the link a use for
 * nothing (FR-082) — and an empty selection is a valid submission
 * (Story 13 scenario 3).
 */
export function FamilyMemberPicker({
  trainerName,
  selectableProfiles,
  onSubmit,
  isPending,
}: FamilyMemberPickerProps) {
  const form = useForm({
    defaultValues: { player_profile_ids: [] as string[] },
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: joinAcceptSchema },
    onSubmit: ({ value }) => onSubmit(value),
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
      <p className="text-body">Who will train with {trainerName}?</p>
      <form.Field name="player_profile_ids">
        {(field) => (
          <div className="flex flex-col gap-2">
            {selectableProfiles.map((profile) => {
              const checked = field.state.value.includes(profile.player_profile_id)
              return (
                <label
                  key={profile.player_profile_id}
                  className="flex items-center gap-2 text-body"
                >
                  <Checkbox
                    checked={checked || profile.already_associated}
                    disabled={profile.already_associated}
                    onCheckedChange={(value) => {
                      if (value) {
                        field.handleChange([...field.state.value, profile.player_profile_id])
                      } else {
                        field.handleChange(
                          field.state.value.filter((id) => id !== profile.player_profile_id),
                        )
                      }
                    }}
                  />
                  <span>
                    {profile.display_name}
                    {profile.already_associated && (
                      <span className="text-muted-foreground"> (already connected)</span>
                    )}
                  </span>
                </label>
              )
            })}
          </div>
        )}
      </form.Field>

      <form.Subscribe selector={(state) => state.isSubmitting}>
        {(isSubmitting) => (
          <Button type="submit" disabled={isSubmitting || isPending}>
            {isPending ? 'Joining…' : `Join ${trainerName}`}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
