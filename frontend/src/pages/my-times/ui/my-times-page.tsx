import { AvailabilityWeekEditor } from '@/features/availability/ui/availability-week-editor'
import { BackButton } from '@/shared/ui/back-button'

/**
 * `/my-times` (US3, FR-024). The coach's own weekly availability —
 * states, revises, and clears a pattern of ranges, saved whole in one
 * transaction (FR-029).
 */
export function MyTimesPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <BackButton fallbackTo="/" className="self-start" />
      <h1 className="text-section-title">My Times</h1>
      <p className="text-muted-foreground text-body">
        State the times you are available to coach. Trainers you work with can see this week.
      </p>
      <AvailabilityWeekEditor subject={{ kind: 'own' }} />
    </div>
  )
}
