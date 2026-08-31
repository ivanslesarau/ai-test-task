import { formatAvailabilitySummary } from '@/entities/availability/model/format-summary'
import type { AvailabilitySlot } from '@/shared/api/types'

interface AvailabilitySummaryProps {
  slots: AvailabilitySlot[]
  updatedAt: string | null
}

/**
 * The one-line "Best times" cell for a roster row (US5, FR-020, FR-034),
 * reading the single formatter in `entities/availability/model/format-summary.ts`
 * so a summary here can never disagree with the full week or the editor
 * (frontend-contracts.md §34). Renders "No times set" — never
 * "Unavailable" — for both never-stated and deliberately-cleared weeks;
 * the revision date is shown only alongside an actual stated week, since
 * a bare "No times set" needs no qualifying date in a compact row.
 */
export function AvailabilitySummary({ slots, updatedAt }: AvailabilitySummaryProps) {
  const summary = formatAvailabilitySummary(slots)

  if (slots.length === 0) {
    return <span className="text-muted-foreground text-body">{summary}</span>
  }

  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-body">{summary}</span>
      {updatedAt && (
        <span className="text-caption text-muted-foreground">
          Updated {new Date(updatedAt).toLocaleDateString()}
        </span>
      )}
    </div>
  )
}
