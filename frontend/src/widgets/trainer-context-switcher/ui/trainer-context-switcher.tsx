import { useSession } from '@/entities/session/api/use-session'
import { isChildAccount } from '@/entities/session/model/role-guards'
import { useOwnContexts } from '@/entities/trainer-context/api/use-contexts'
import { useSwitchTrainingContext } from '@/entities/trainer-context/api/use-switch-context'
import type { TrainingContextEntry } from '@/shared/api/types'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'
import { TrainerContextLabel } from '@/widgets/trainer-context-switcher/ui/trainer-context-label'

function pairValue(entry: TrainingContextEntry): string {
  return `${entry.player_profile_id}:${entry.trainer_id}`
}

/**
 * Renders the switchable dropdown only when the session reports more
 * than one switchable context (FR-118) — `session.context_count`, the
 * direct replacement for `trainer_count`. At exactly one, this component
 * renders `TrainerContextLabel` instead, so the shell keeps a single slot
 * for "who the player is with" whether that is stated by a control or by
 * plain text (fix F7/T307). Reads the list from `useOwnContexts`, not
 * from the session — the session carries only the count and the active
 * pair.
 *
 * **Regrouped for family accounts** (frontend-contracts.md §19, FR-118,
 * FR-119): a parent-shaped account's entries group by
 * `player_profile_kind` — `self` under "Your Training", `child` under
 * "Your Children's Training" — with an empty group rendering no heading
 * at all. A signed-in child's list is flat and holds no grouping,
 * because every entry names the one profile they are. The server is what
 * guarantees a child's list never contains a sibling (R-48); this widget
 * only renders what it is given.
 */
export function TrainerContextSwitcher() {
  const { data: session } = useSession()
  const contexts = useOwnContexts()
  const switchContext = useSwitchTrainingContext()

  if (!session || session.context_count === 0) return null
  if (session.context_count === 1) return <TrainerContextLabel />
  if (!contexts.data) return null

  const activeValue =
    session.active_player_profile_id && session.active_trainer_id
      ? `${session.active_player_profile_id}:${session.active_trainer_id}`
      : undefined

  function handleChange(value: string) {
    const [playerProfileId, trainerId] = value.split(':')
    if (!playerProfileId || !trainerId) return
    switchContext.mutate({ playerProfileId, trainerId })
  }

  const entries = contexts.data.contexts
  const selfEntries = entries.filter((entry) => entry.player_profile_kind === 'self')
  const childEntries = entries.filter((entry) => entry.player_profile_kind === 'child')

  return (
    <Select value={activeValue} onValueChange={handleChange} disabled={switchContext.isPending}>
      <SelectTrigger aria-label="Switch trainer" className="w-56">
        <SelectValue placeholder="Select a trainer" />
      </SelectTrigger>
      <SelectContent>
        {isChildAccount(session) ? (
          entries.map((entry) => (
            <SelectItem key={pairValue(entry)} value={pairValue(entry)}>
              {entry.trainer_display_name}
            </SelectItem>
          ))
        ) : (
          <>
            {selfEntries.length > 0 && (
              <SelectGroup>
                <SelectLabel>Your Training</SelectLabel>
                {selfEntries.map((entry) => (
                  <SelectItem key={pairValue(entry)} value={pairValue(entry)}>
                    {entry.player_display_name} (Me) → {entry.trainer_display_name}
                  </SelectItem>
                ))}
              </SelectGroup>
            )}
            {childEntries.length > 0 && (
              <SelectGroup>
                <SelectLabel>Your Children&rsquo;s Training</SelectLabel>
                {childEntries.map((entry) => (
                  <SelectItem key={pairValue(entry)} value={pairValue(entry)}>
                    {entry.player_display_name} → {entry.trainer_display_name}
                  </SelectItem>
                ))}
              </SelectGroup>
            )}
          </>
        )}
      </SelectContent>
    </Select>
  )
}
