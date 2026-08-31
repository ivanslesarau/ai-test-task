import { z } from 'zod'

/**
 * The availability invariants (data-model.md §103, research.md R2-08,
 * R2-21) — mirrors `backend/src/app/core/availability_rules.py` exactly,
 * so the two sides cannot drift (Principle II boundary parity).
 */
export const MINUTES_PER_SLOT_STEP = 15
export const MAX_SLOTS_PER_DAY = 6
export const DAYS_IN_WEEK = 7
export const MINUTES_IN_DAY = 1440

/** Full day names, Monday first (`day_of_week` 0-6) — used only for
 * naming the offending day in a validation message (FR-027). This is
 * NOT the summary formatter (research.md R2-12): `format-summary.ts`
 * alone owns clock format and abbreviations for display. */
const DAY_NAMES = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
] as const

export const availabilitySlotSchema = z
  .object({
    day_of_week: z.number().int().min(0).max(DAYS_IN_WEEK - 1),
    start_minute: z
      .number()
      .int()
      .min(0)
      .max(MINUTES_IN_DAY - MINUTES_PER_SLOT_STEP)
      .refine((m) => m % MINUTES_PER_SLOT_STEP === 0, {
        message: `Times must fall on a ${MINUTES_PER_SLOT_STEP}-minute grid.`,
      }),
    end_minute: z
      .number()
      .int()
      .min(MINUTES_PER_SLOT_STEP)
      .max(MINUTES_IN_DAY)
      .refine((m) => m % MINUTES_PER_SLOT_STEP === 0, {
        message: `Times must fall on a ${MINUTES_PER_SLOT_STEP}-minute grid.`,
      }),
  })
  .refine((s) => s.start_minute < s.end_minute, {
    path: ['end_minute'],
    message: 'A range must start before it ends.',
  })

export type AvailabilitySlotValue = z.infer<typeof availabilitySlotSchema>

/**
 * The pure set-level validator (data-model.md §111.2, FR-027, FR-028),
 * mirroring `backend/src/app/services/availability_service.py:validate_week`
 * exactly: at most `MAX_SLOTS_PER_DAY` a day, and no two ranges on one day
 * overlap — sorted by `start_minute`, an overlap is `next.start <
 * previous.end`; touching ranges (`next.start === previous.end`) are
 * valid. Returns a map keyed by `day_of_week`, the same key shape the
 * server's `ValidationFailure.fields` uses (`str(day_of_week)`), so a
 * server 422 and a client-side refusal render through one code path
 * (`AvailabilityWeekEditor`).
 */
export function computeDayErrors(
  slots: readonly Pick<AvailabilitySlotValue, 'day_of_week' | 'start_minute' | 'end_minute'>[],
): Record<number, string> {
  const byDay = new Map<number, typeof slots[number][]>()
  for (const slot of slots) {
    const existing = byDay.get(slot.day_of_week)
    if (existing) existing.push(slot)
    else byDay.set(slot.day_of_week, [slot])
  }

  const errors: Record<number, string> = {}
  for (const [day, daySlots] of byDay) {
    if (daySlots.length > MAX_SLOTS_PER_DAY) {
      errors[day] = `No more than ${MAX_SLOTS_PER_DAY} ranges are allowed in a day.`
      continue
    }
    const ordered = [...daySlots].sort((a, b) => a.start_minute - b.start_minute)
    for (let i = 1; i < ordered.length; i += 1) {
      const previous = ordered[i - 1]
      const current = ordered[i]
      if (previous && current && current.start_minute < previous.end_minute) {
        errors[day] = 'Ranges on this day overlap.'
        break
      }
    }
  }
  return errors
}

/** The day name a `computeDayErrors` key refers to — used to build a
 * message naming the day (FR-027) without duplicating `DAY_NAMES`. */
export function dayName(dayOfWeek: number): string {
  return DAY_NAMES[dayOfWeek] ?? `day ${dayOfWeek}`
}

function validateWeek(value: { slots: AvailabilitySlotValue[] }, ctx: z.RefinementCtx): void {
  const dayErrors = computeDayErrors(value.slots)
  for (const [day, message] of Object.entries(dayErrors)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: `${dayName(Number(day))}: ${message}`,
      path: ['slots'],
    })
  }
}

/** The whole-week payload, matching `AvailabilityWeekUpdate`
 * (contracts/openapi.yaml). The set-level rules (FR-027, FR-028) are
 * applied once over the whole array via `superRefine`, mirroring the
 * server's `validate_week` (data-model.md §111.2, frontend-contracts.md
 * §32). */
export const availabilityWeekSchema = z
  .object({
    slots: z.array(availabilitySlotSchema).max(MAX_SLOTS_PER_DAY * DAYS_IN_WEEK),
  })
  .superRefine(validateWeek)

export type AvailabilityWeekFormValues = { slots: AvailabilitySlotValue[] }
