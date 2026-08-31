import { useSession } from '@/entities/session/api/use-session'
import { useOwnContexts } from '@/entities/trainer-context/api/use-contexts'
import { AvailabilityWeekEditor } from '@/features/availability/ui/availability-week-editor'
import { BackButton } from '@/shared/ui/back-button'

/**
 * `/availability` (US4, FR-025, FR-033). The family's per-profile
 * weekly availability, reusing the existing training-context/profile
 * switcher's selection rather than inventing a second source of truth
 * for "whose data am I looking at" (frontend-contracts.md §33) — a
 * sibling's week getting saved onto the wrong profile is exactly the bug
 * a second selector would risk. The switcher itself already lives in
 * `AppShell`'s header for every `player_parent` session, so this page
 * only reads its current selection rather than rendering a second copy
 * of the control. The selected profile's name is shown unmistakably
 * above the editor.
 */
export function AvailabilityPage() {
  const { data: session } = useSession()
  const contexts = useOwnContexts()

  const activeEntry = contexts.data?.contexts.find(
    (entry) =>
      entry.player_profile_id === session?.active_player_profile_id &&
      entry.trainer_id === session.active_trainer_id,
  )

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <BackButton fallbackTo="/" className="self-start" />
      <h1 className="text-section-title">Availability</h1>

      {!session?.active_player_profile_id && (
        <p className="text-muted-foreground text-body">
          Select a trainer above to state times for that player.
        </p>
      )}

      {session?.active_player_profile_id && (
        <>
          <p className="text-body">
            Stating times for{' '}
            <span className="font-medium" data-testid="availability-active-profile">
              {activeEntry?.player_display_name ?? 'this player'}
            </span>
            .
          </p>
          <AvailabilityWeekEditor
            key={session.active_player_profile_id}
            subject={{ kind: 'profile', profileId: session.active_player_profile_id }}
          />
        </>
      )}
    </div>
  )
}
