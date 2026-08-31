import {
  formatAvailabilityWeekRows,
  NO_TIMES_SET,
} from '@/entities/availability/model/format-summary'
import type { AvailabilityWeek } from '@/shared/api/types'

interface AvailabilityWeekViewProps {
  week: AvailabilityWeek
}

/**
 * The read-only full week — owner-agnostic, shared by every place a
 * week is displayed rather than edited (US5's trainer-facing detail
 * pages read through this same component later). Renders absence
 * identically to the editor's own empty state (frontend-contracts.md
 * §34, FR-035): `updated_at === null` (never stated) and a non-null
 * `updated_at` with no slots (deliberately cleared) both read "No times
 * set" — never "Unavailable" — the second with its revision date shown
 * alongside so a viewer can tell the two apart.
 */
export function AvailabilityWeekView({ week }: AvailabilityWeekViewProps) {
  if (week.slots.length === 0) {
    return (
      <div className="flex flex-col gap-1">
        <p className="text-muted-foreground text-body">{NO_TIMES_SET}</p>
        {week.updated_at && (
          <p className="text-caption text-muted-foreground">
            Cleared on {new Date(week.updated_at).toLocaleDateString()}
          </p>
        )}
      </div>
    )
  }

  const rows = formatAvailabilityWeekRows(week.slots)
  return (
    <div className="flex flex-col gap-1">
      {rows.map((row) => (
        <div key={row.dayOfWeek} className="flex items-baseline justify-between gap-4 text-body">
          <span className="font-medium">{row.dayName}</span>
          <span className="text-muted-foreground">
            {row.ranges.length > 0 ? row.ranges.join(', ') : '—'}
          </span>
        </div>
      ))}
      {week.updated_at && (
        <p className="text-caption text-muted-foreground">
          Last revised {new Date(week.updated_at).toLocaleDateString()}
        </p>
      )}
    </div>
  )
}
