import { useSession } from '@/entities/session/api/use-session'
import { useOwnTrainers } from '@/entities/trainer-context/api/use-trainers'

/**
 * Static text naming the active trainer for a player/parent connected to
 * exactly one of them. FR-088 correctly hides the switcher at that point,
 * but without this a player who has just joined lands on "Welcome back."
 * with nothing naming whose portal they are in (FR-062, fix F7/T307).
 * Reads `active_trainer_id` from the session and the display name from
 * `userKeys.trainers`, the same list the switcher itself reads.
 */
export function TrainerContextLabel() {
  const { data: session } = useSession()
  const trainers = useOwnTrainers()

  if (!session?.active_trainer_id) return null

  const activeTrainer = trainers.data?.trainers.find(
    (trainer) => trainer.trainer_id === session.active_trainer_id,
  )
  if (!activeTrainer) return null

  return <p className="text-body">{activeTrainer.display_name}</p>
}
