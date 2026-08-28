import { useState } from 'react'

import { revalidateLogic, useForm } from '@tanstack/react-form'

import { useOwnContexts } from '@/entities/trainer-context/api/use-contexts'
import { useCreateChildProfile } from '@/entities/player-profile/api/use-create-child'
import { getDuplicateMatches } from '@/features/family/add-child/model/duplicate-error'
import { createChildProfileSchema } from '@/features/family/add-child/model/schema'
import type { CreateChildProfileValues } from '@/features/family/add-child/model/schema'
import { DuplicateProfileDialog } from '@/features/family/add-child/ui/duplicate-dialog'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'
import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'
import type { CreateChildProfileRequest, Gender, PlayerProfile } from '@/shared/api/types'
import { Button } from '@/shared/ui/button'
import { Checkbox } from '@/shared/ui/checkbox'
import { FormItem, FormLabel, FormMessage } from '@/shared/ui/form-field'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
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

const DEFAULT_VALUES: CreateChildProfileValues = {
  first_name: '',
  last_name: '',
  date_of_birth: '',
  gender: '' as unknown as Gender,
  school: '',
  jersey_number: '',
  trainer_ids: [],
  acknowledge_possible_duplicate: false,
}

interface AddChildFormProps {
  onSuccess: (profile: PlayerProfile) => void
}

/**
 * `POST /me/players` (US9, FR-106 - FR-110, FR-122, FR-123). The trainer
 * question renders in the three shapes FR-122 describes: nothing at all
 * when the account trains with nobody, a single yes/no naming the one
 * trainer, or a checklist for several.
 */
export function AddChildForm({ onSuccess }: AddChildFormProps) {
  const createChild = useCreateChildProfile()
  const { data: contexts } = useOwnContexts()
  const [duplicateMatches, setDuplicateMatches] = useState<PlayerProfile[] | null>(null)

  // One row per trainer the account is already associated with through
  // any profile — de-duplicated, since the same trainer can appear once
  // per profile the account already has.
  const availableTrainers = Array.from(
    new Map(
      (contexts?.contexts ?? []).map((entry) => [
        entry.trainer_id,
        { id: entry.trainer_id, name: entry.trainer_display_name },
      ]),
    ).values(),
  )

  const form = useForm({
    defaultValues: DEFAULT_VALUES,
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: createChildProfileSchema },
    onSubmit: ({ value }) => {
      submit(value)
    },
  })

  function submit(value: CreateChildProfileValues) {
    const normalized = normalizeEmptyToNull(value) as CreateChildProfileValues
    const body: CreateChildProfileRequest = {
      first_name: normalized.first_name,
      last_name: normalized.last_name,
      date_of_birth: normalized.date_of_birth,
      gender: normalized.gender,
      school: normalized.school || null,
      jersey_number: normalized.jersey_number || null,
      trainer_ids: normalized.trainer_ids,
      acknowledge_possible_duplicate: normalized.acknowledge_possible_duplicate,
    }
    createChild.mutate(body, {
      onSuccess: (profile) => {
        setDuplicateMatches(null)
        onSuccess(profile)
      },
      onError: (error) => {
        const matches = getDuplicateMatches(error)
        if (matches) {
          setDuplicateMatches(matches)
          return
        }
        form.setErrorMap({
          onServer: toServerErrorMap(error),
        } as unknown as Parameters<typeof form.setErrorMap>[0])
      },
    })
  }

  return (
    <>
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
                <FormLabel htmlFor={field.name}>School (optional)</FormLabel>
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

          <form.Field name="jersey_number">
            {(field) => (
              <FormItem>
                <FormLabel htmlFor={field.name}>Jersey number (optional)</FormLabel>
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

        {/* FR-122's three shapes: nothing at all with no trainer, a single
            yes/no with exactly one, a checklist with several. */}
        {availableTrainers.length === 1 && availableTrainers[0] && (
          <form.Field name="trainer_ids">
            {(field) => {
              const trainer = availableTrainers[0]
              if (!trainer) return null
              const checked = field.state.value.includes(trainer.id)
              return (
                <FormItem>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="single-trainer"
                      checked={checked}
                      onCheckedChange={(value) =>
                        field.handleChange(value === true ? [trainer.id] : [])
                      }
                    />
                    <Label htmlFor="single-trainer">
                      Also connect this child with {trainer.name}
                    </Label>
                  </div>
                </FormItem>
              )
            }}
          </form.Field>
        )}

        {availableTrainers.length > 1 && (
          <form.Field name="trainer_ids">
            {(field) => (
              <FormItem>
                <FormLabel>Which trainers does this child train with?</FormLabel>
                <div className="flex flex-col gap-2">
                  {availableTrainers.map((trainer) => {
                    const checked = field.state.value.includes(trainer.id)
                    return (
                      <div key={trainer.id} className="flex items-center gap-2">
                        <Checkbox
                          id={`trainer-${trainer.id}`}
                          checked={checked}
                          onCheckedChange={(value) =>
                            field.handleChange(
                              value === true
                                ? [...field.state.value, trainer.id]
                                : field.state.value.filter((id) => id !== trainer.id),
                            )
                          }
                        />
                        <Label htmlFor={`trainer-${trainer.id}`}>{trainer.name}</Label>
                      </div>
                    )
                  })}
                </div>
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
              {isSubmitting ? 'Adding…' : 'Add child'}
            </Button>
          )}
        </form.Subscribe>
      </form>

      {duplicateMatches && (
        <DuplicateProfileDialog
          matches={duplicateMatches}
          isConfirming={createChild.isPending}
          onCancel={() => setDuplicateMatches(null)}
          onConfirm={() => {
            submit({ ...form.state.values, acknowledge_possible_duplicate: true })
          }}
        />
      )}
    </>
  )
}
