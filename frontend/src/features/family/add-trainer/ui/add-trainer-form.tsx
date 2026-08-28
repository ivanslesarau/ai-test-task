import { revalidateLogic, useForm } from '@tanstack/react-form'
import { toast } from 'sonner'

import { useOwnContexts } from '@/entities/trainer-context/api/use-contexts'
import { useAddPlayerTrainer } from '@/entities/player-profile/api/use-player-trainers'
import { addPlayerTrainerSchema } from '@/features/family/add-trainer/model/schema'
import { fieldErrorText, toServerErrorMap } from '@/shared/lib/form-errors'
import { normalizeEmptyToNull } from '@/shared/lib/normalize-payload'
import type { AddPlayerTrainerRequest } from '@/shared/api/types'
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

interface AddTrainerFormProps {
  profileId: string
  /** Trainer ids already associated with this profile — excluded from the
   * "choose an existing trainer" list, since offering one already active
   * would just reproduce the no-op the server itself already handles. */
  existingTrainerIds: string[]
  onSuccess?: () => void
}

/**
 * `POST /me/players/{profile_id}/trainers` (US10, FR-125, FR-127). Two
 * ways in, exactly as the backend accepts: an invitation code, or a
 * trainer the account already trains with through another profile.
 */
export function AddTrainerForm({ profileId, existingTrainerIds, onSuccess }: AddTrainerFormProps) {
  const addTrainer = useAddPlayerTrainer()
  const { data: contexts } = useOwnContexts()

  const candidateTrainers = Array.from(
    new Map(
      (contexts?.contexts ?? [])
        .filter((entry) => !existingTrainerIds.includes(entry.trainer_id))
        .map((entry) => [entry.trainer_id, { id: entry.trainer_id, name: entry.trainer_display_name }]),
    ).values(),
  )

  const form = useForm({
    defaultValues: { code: '', trainer_id: '' },
    validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
    validators: { onDynamic: addPlayerTrainerSchema },
    onSubmit: ({ value }) => {
      const normalized = normalizeEmptyToNull(value)
      const body: AddPlayerTrainerRequest = normalized.code
        ? { code: normalized.code }
        : { trainer_id: normalized.trainer_id }
      addTrainer.mutate(
        { profileId, body },
        {
          onSuccess: () => {
            toast.success('Trainer added')
            form.reset()
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
      <form.Field name="code">
        {(field) => (
          <FormItem>
            <FormLabel htmlFor={field.name}>Invitation code</FormLabel>
            <Input
              id={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(event) => field.handleChange(event.target.value)}
              placeholder="Paste a trainer's invitation code"
            />
            <FormMessage>{fieldErrorText(field.state.meta.errors)}</FormMessage>
          </FormItem>
        )}
      </form.Field>

      {candidateTrainers.length > 0 && (
        <form.Field name="trainer_id">
          {(field) => (
            <FormItem>
              <FormLabel htmlFor={field.name}>Or choose a trainer you already train with</FormLabel>
              <Select value={field.state.value} onValueChange={(value) => field.handleChange(value)}>
                <SelectTrigger id={field.name}>
                  <SelectValue placeholder="Select a trainer" />
                </SelectTrigger>
                <SelectContent>
                  {candidateTrainers.map((trainer) => (
                    <SelectItem key={trainer.id} value={trainer.id}>
                      {trainer.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
            {isSubmitting ? 'Adding…' : 'Add trainer'}
          </Button>
        )}
      </form.Subscribe>
    </form>
  )
}
