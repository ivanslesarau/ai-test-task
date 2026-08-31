import type { AvailabilitySlot, AvailabilityWeek } from '@/shared/api/types'

/**
 * The ONE summary-formatting module in the whole codebase (research.md
 * R2-12, frontend-contracts.md §34). The API returns structured
 * `{day_of_week, start_minute, end_minute}` triples and NEVER a
 * pre-baked string — day names, the 12-hour clock, and the en-dash are
 * presentation, and belong here alone, so the summary in a roster row
 * and the heading of a full-week view can never disagree.
 */

const DAY_ABBREVIATIONS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const
const DAY_FULL_NAMES = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
] as const

export const NO_TIMES_SET = 'No times set'

/** Also exported for the quarter-hour picker (`day-ranges-field.tsx`) —
 * still the only place a clock format is computed; the picker just reuses
 * it rather than growing a second implementation. */
export function formatClock(minute: number): string {
  const totalMinutes = minute % 1440
  const hour24 = Math.floor(totalMinutes / 60)
  const minutePart = totalMinutes % 60
  const period = hour24 < 12 ? 'am' : 'pm'
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12
  const minuteText = minutePart === 0 ? '' : `:${String(minutePart).padStart(2, '0')}`
  return `${hour12}${minuteText}${period}`
}

function formatRange(slot: AvailabilitySlot): string {
  return `${formatClock(slot.start_minute)}–${formatClock(slot.end_minute)}`
}

function groupByDay(slots: readonly AvailabilitySlot[]): Map<number, AvailabilitySlot[]> {
  const byDay = new Map<number, AvailabilitySlot[]>()
  for (const slot of slots) {
    const existing = byDay.get(slot.day_of_week)
    if (existing) existing.push(slot)
    else byDay.set(slot.day_of_week, [slot])
  }
  for (const daySlots of byDay.values()) {
    daySlots.sort((a, b) => a.start_minute - b.start_minute)
  }
  return byDay
}

/**
 * One line: `"Mon 5-8pm, Wed 6-9pm"`. A day with no ranges is absent
 * rather than listed as "Not available" (frontend-contracts.md §34), so
 * the summary stays short. Renders `"No times set"` — never
 * "Unavailable" — for both never-stated (`updated_at: null`) and
 * deliberately-cleared (`updated_at` set, `slots: []`) weeks (FR-035):
 * this function only ever looks at `slots`, so the two cases collapse to
 * the same rendering by construction.
 */
export function formatAvailabilitySummary(slots: readonly AvailabilitySlot[]): string {
  if (slots.length === 0) return NO_TIMES_SET

  const byDay = groupByDay(slots)
  const parts: string[] = []
  for (let day = 0; day < DAY_ABBREVIATIONS.length; day += 1) {
    const daySlots = byDay.get(day)
    if (!daySlots || daySlots.length === 0) continue
    const ranges = daySlots.map(formatRange).join(', ')
    parts.push(`${DAY_ABBREVIATIONS[day]} ${ranges}`)
  }
  return parts.length > 0 ? parts.join(', ') : NO_TIMES_SET
}

export interface WeekRow {
  dayOfWeek: number
  dayName: string
  ranges: string[]
}

/** Every day of the week, in order, each carrying its own formatted
 * ranges (empty when the day has none) — the full-week view marks the
 * empty days rather than omitting them (frontend-contracts.md §34). */
export function formatAvailabilityWeekRows(slots: readonly AvailabilitySlot[]): WeekRow[] {
  const byDay = groupByDay(slots)
  return DAY_FULL_NAMES.map((name, dayOfWeek) => ({
    dayOfWeek,
    dayName: name,
    ranges: (byDay.get(dayOfWeek) ?? []).map(formatRange),
  }))
}

/**
 * The three "no times set" rules of frontend-contracts.md §34, in one
 * place: `updated_at === null` (never stated) and a non-null
 * `updated_at` with no slots (deliberately cleared) both render as "No
 * times set" — never "Unavailable" — with the revision date shown
 * alongside only in the second case. Returns `null` when there IS
 * something to render (the caller falls back to the ranges themselves).
 */
export function noTimesSetLabel(week: Pick<AvailabilityWeek, 'slots' | 'updated_at'>): string | null {
  if (week.slots.length > 0) return null
  return NO_TIMES_SET
}
