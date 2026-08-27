import { useSession } from '@/entities/session/api/use-session'
import { useSwitchTrainerContext } from '@/entities/trainer-context/api/use-switch-context'
import { useOwnTrainers } from '@/entities/trainer-context/api/use-trainers'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'

/**
 * Renders only when the session reports more than one switchable
 * trainer (FR-088). Reads the list from `useOwnTrainers`, not from the
 * session — the session carries only the count and the active id.
 */
export function TrainerContextSwitcher() {
  const { data: session } = useSession()
  const trainers = useOwnTrainers()
  const switchContext = useSwitchTrainerContext()

  if (!session || session.trainer_count <= 1) return null
  if (!trainers.data) return null

  return (
    <Select
      value={session.active_trainer_id ?? undefined}
      onValueChange={(trainerId) => switchContext.mutate(trainerId)}
      disabled={switchContext.isPending}
    >
      <SelectTrigger aria-label="Switch trainer" className="w-48">
        <SelectValue placeholder="Select a trainer" />
      </SelectTrigger>
      <SelectContent>
        {trainers.data.trainers.map((trainer) => (
          <SelectItem key={trainer.trainer_id} value={trainer.trainer_id}>
            {trainer.display_name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
