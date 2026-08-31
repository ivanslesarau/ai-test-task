import { describe, expect, it } from 'vitest'

import {
  availabilitySlotSchema,
  availabilityWeekSchema,
  computeDayErrors,
  dayName,
} from '@/entities/availability/model/week'

describe('computeDayErrors', () => {
  it('is empty for an empty week', () => {
    expect(computeDayErrors([])).toEqual({})
  })

  it('accepts touching ranges on the same day', () => {
    const errors = computeDayErrors([
      { day_of_week: 1, start_minute: 540, end_minute: 600 },
      { day_of_week: 1, start_minute: 600, end_minute: 660 },
    ])
    expect(errors).toEqual({})
  })

  it('names the day for overlapping ranges, regardless of submission order', () => {
    const errors = computeDayErrors([
      { day_of_week: 2, start_minute: 600, end_minute: 720 },
      { day_of_week: 2, start_minute: 540, end_minute: 660 },
    ])
    expect(errors[2]).toMatch(/overlap/i)
    expect(errors[0]).toBeUndefined()
  })

  it('names the day for more than six ranges', () => {
    const slots = Array.from({ length: 7 }, (_, i) => ({
      day_of_week: 0,
      start_minute: i * 60,
      end_minute: i * 60 + 30,
    }))
    const errors = computeDayErrors(slots)
    expect(errors[0]).toMatch(/no more than 6/i)
  })

  it('accepts exactly six ranges', () => {
    const slots = Array.from({ length: 6 }, (_, i) => ({
      day_of_week: 0,
      start_minute: i * 60,
      end_minute: i * 60 + 30,
    }))
    expect(computeDayErrors(slots)).toEqual({})
  })

  it('keeps unrelated days error-free', () => {
    const errors = computeDayErrors([
      { day_of_week: 3, start_minute: 540, end_minute: 660 },
      { day_of_week: 3, start_minute: 600, end_minute: 720 },
      { day_of_week: 4, start_minute: 540, end_minute: 600 },
    ])
    expect(errors[3]).toMatch(/overlap/i)
    expect(errors[4]).toBeUndefined()
  })
})

describe('dayName', () => {
  it('names Monday as day 0', () => {
    expect(dayName(0)).toBe('Monday')
  })

  it('names Sunday as day 6', () => {
    expect(dayName(6)).toBe('Sunday')
  })
})

describe('availabilitySlotSchema', () => {
  it('accepts a valid slot', () => {
    const result = availabilitySlotSchema.safeParse({
      day_of_week: 0,
      start_minute: 540,
      end_minute: 600,
    })
    expect(result.success).toBe(true)
  })

  it('refuses a start on or after its end', () => {
    const result = availabilitySlotSchema.safeParse({
      day_of_week: 0,
      start_minute: 600,
      end_minute: 600,
    })
    expect(result.success).toBe(false)
  })

  it('refuses an off-grid start', () => {
    const result = availabilitySlotSchema.safeParse({
      day_of_week: 0,
      start_minute: 545,
      end_minute: 600,
    })
    expect(result.success).toBe(false)
  })

  it('refuses a range past the end of the day', () => {
    const result = availabilitySlotSchema.safeParse({
      day_of_week: 0,
      start_minute: 1425,
      end_minute: 1470,
    })
    expect(result.success).toBe(false)
  })

  it('accepts a range ending exactly at midnight', () => {
    const result = availabilitySlotSchema.safeParse({
      day_of_week: 6,
      start_minute: 1380,
      end_minute: 1440,
    })
    expect(result.success).toBe(true)
  })
})

describe('availabilityWeekSchema', () => {
  it('accepts a valid week', () => {
    const result = availabilityWeekSchema.safeParse({
      slots: [{ day_of_week: 0, start_minute: 540, end_minute: 600 }],
    })
    expect(result.success).toBe(true)
  })

  it('refuses a week with overlapping ranges', () => {
    const result = availabilityWeekSchema.safeParse({
      slots: [
        { day_of_week: 0, start_minute: 540, end_minute: 660 },
        { day_of_week: 0, start_minute: 600, end_minute: 720 },
      ],
    })
    expect(result.success).toBe(false)
  })

  it('accepts an empty week', () => {
    const result = availabilityWeekSchema.safeParse({ slots: [] })
    expect(result.success).toBe(true)
  })
})
