import { describe, expect, it } from 'vitest'

import {
  formatAvailabilitySummary,
  formatAvailabilityWeekRows,
  NO_TIMES_SET,
} from '@/entities/availability/model/format-summary'
import type { AvailabilitySlot } from '@/shared/api/types'

describe('formatAvailabilitySummary', () => {
  it('renders "No times set" for no slots', () => {
    expect(formatAvailabilitySummary([])).toBe(NO_TIMES_SET)
  })

  it('never renders "Unavailable"', () => {
    expect(formatAvailabilitySummary([])).not.toMatch(/unavailable/i)
  })

  it('formats one range in 12-hour clock with an en dash', () => {
    const slots: AvailabilitySlot[] = [{ day_of_week: 0, start_minute: 1020, end_minute: 1200 }]
    expect(formatAvailabilitySummary(slots)).toBe('Mon 5pm–8pm')
  })

  it('joins multiple days and multiple ranges on one day', () => {
    const slots: AvailabilitySlot[] = [
      { day_of_week: 0, start_minute: 1020, end_minute: 1200 },
      { day_of_week: 2, start_minute: 1080, end_minute: 1260 },
    ]
    expect(formatAvailabilitySummary(slots)).toBe('Mon 5pm–8pm, Wed 6pm–9pm')
  })

  it('omits a day with no ranges rather than listing it as unavailable', () => {
    const slots: AvailabilitySlot[] = [{ day_of_week: 5, start_minute: 540, end_minute: 600 }]
    const summary = formatAvailabilitySummary(slots)
    expect(summary).not.toMatch(/mon/i)
    expect(summary).toMatch(/sat/i)
  })
})

describe('formatAvailabilityWeekRows', () => {
  it('returns all seven days in order, even with no slots', () => {
    const rows = formatAvailabilityWeekRows([])
    expect(rows).toHaveLength(7)
    expect(rows[0]).toEqual({ dayOfWeek: 0, dayName: 'Monday', ranges: [] })
    expect(rows[6]).toEqual({ dayOfWeek: 6, dayName: 'Sunday', ranges: [] })
  })

  it('carries formatted ranges for a stated day', () => {
    const slots: AvailabilitySlot[] = [{ day_of_week: 1, start_minute: 540, end_minute: 600 }]
    const rows = formatAvailabilityWeekRows(slots)
    expect(rows[1]?.ranges).toEqual(['9am–10am'])
  })
})
