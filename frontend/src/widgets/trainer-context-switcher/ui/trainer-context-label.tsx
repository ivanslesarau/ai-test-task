import { useSession } from '@/entities/session/api/use-session'
import { useOwnContexts } from '@/entities/trainer-context/api/use-contexts'

/**
 * Static text naming the active trainer for an account connected to
 * exactly one switchable context. FR-118/FR-119 correctly hide the
 * switcher at that point, but without this a player who has just joined
 * lands on "Welcome back." with nothing naming whose portal they are in
 * (FR-062, fix F7/T307). Reads the active pair from the session and the
 * display name from `useOwnContexts`, the same list the switcher itself
 * reads.
 */
export function TrainerContextLabel() {
  const { data: session } = useSession()
  const contexts = useOwnContexts()

  if (!session?.active_trainer_id) return null

  const activeEntry = contexts.data?.contexts.find(
    (entry) =>
      entry.trainer_id === session.active_trainer_id &&
      entry.player_profile_id === session.active_player_profile_id,
  )
  if (!activeEntry) return null

  return <p className="text-body">{activeEntry.trainer_display_name}</p>
}
