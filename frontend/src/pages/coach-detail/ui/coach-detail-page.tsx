import { useCoachDetail } from '@/entities/coach/api/use-coach-detail'
import { AvailabilityWeekView } from '@/features/availability/ui/availability-week-view'
import { Route as CoachDetailRoute } from '@/routes/_authed/trainer/coaches.$coachUserId'
import { BackButton } from '@/shared/ui/back-button'

/**
 * One coach on the trainer's roster: their profile summary and their
 * full stated week, read-only (US5, FR-034, FR-037,
 * frontend-contracts.md §30). No control anywhere on this page can edit
 * the coach's own times — stated times are the coach's own.
 */
export function CoachDetailPage() {
  const { coachUserId } = CoachDetailRoute.useParams()
  const { data: coach, isLoading, isError } = useCoachDetail(coachUserId)

  if (isLoading) return <p className="p-6 text-muted-foreground">Loading…</p>
  if (isError || !coach) return <p className="p-6 text-destructive">Could not load this coach.</p>

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
      <BackButton fallbackTo="/trainer/coaches" className="self-start" />
      <h1 className="text-section-title">
        {coach.first_name} {coach.last_name}
      </h1>
      <dl className="grid grid-cols-2 gap-2 text-body">
        <dt className="text-muted-foreground">Email</dt>
        <dd>{coach.email}</dd>
        <dt className="text-muted-foreground">Joined</dt>
        <dd>{new Date(coach.joined_at).toLocaleDateString()}</dd>
      </dl>
      <div className="flex flex-col gap-2">
        <h2 className="text-card-title">Availability</h2>
        <AvailabilityWeekView
          week={{ slots: coach.availability, updated_at: coach.availability_updated_at }}
        />
      </div>
    </div>
  )
}
