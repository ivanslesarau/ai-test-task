import { useEffect, useState } from 'react'

import type { WritableAvailabilitySubject } from '@/entities/availability/api/query-keys'
import { useAvailability } from '@/entities/availability/api/use-availability'
import { useClearAvailability } from '@/entities/availability/api/use-clear-availability'
import { useSaveAvailability } from '@/entities/availability/api/use-save-availability'
import { computeDayErrors, dayName, DAYS_IN_WEEK } from '@/entities/availability/model/week'
import { DayRangesField } from '@/features/availability/ui/day-ranges-field'
import { isApiError } from '@/shared/api/errors'
import type { AvailabilitySlot } from '@/shared/api/types'
import { Button } from '@/shared/ui/button'

interface IndexedSlot extends AvailabilitySlot {
  absoluteIndex: number
}

function withIndices(slots: AvailabilitySlot[]): IndexedSlot[] {
  return slots.map((slot, absoluteIndex) => ({ ...slot, absoluteIndex }))
}

function groupByDay(slots: IndexedSlot[]): Map<number, IndexedSlot[]> {
  const byDay = new Map<number, IndexedSlot[]>()
  for (const slot of slots) {
    const existing = byDay.get(slot.day_of_week)
    if (existing) existing.push(slot)
    else byDay.set(slot.day_of_week, [slot])
  }
  return byDay
}

/** Reads the server's day-keyed `422` (`fields: {"0": "...", ...}`,
 * `str(day_of_week)`, data-model.md §111.2) into the same
 * `Record<number, string>` shape the client-side validator produces, so
 * both render through one path (frontend-contracts.md §32). */
function dayErrorsFromApiError(error: unknown): Record<number, string> {
  if (!isApiError(error)) return {}
  const dayErrors: Record<number, string> = {}
  for (const fieldError of error.fields) {
    const day = Number(fieldError.field)
    if (Number.isInteger(day) && day >= 0 && day < DAYS_IN_WEEK) {
      dayErrors[day] = fieldError.message
    }
  }
  return dayErrors
}

interface AvailabilityWeekEditorProps {
  subject: WritableAvailabilitySubject
}

/**
 * The whole-week editor — ONE form for the whole week, not one per day
 * and not one per range (frontend-contracts.md §33): the backend
 * replaces the week atomically (FR-029), so a per-day save would let a
 * user believe a day saved when only the whole week does. Owner-agnostic
 * — used identically for a coach's own week and a family's per-profile
 * week.
 */
export function AvailabilityWeekEditor({ subject }: AvailabilityWeekEditorProps) {
  const { data, isLoading, isError } = useAvailability(subject)
  const save = useSaveAvailability(subject)
  const clear = useClearAvailability(subject)

  const [slots, setSlots] = useState<AvailabilitySlot[] | null>(null)
  const [dayErrors, setDayErrors] = useState<Record<number, string>>({})

  // Local editable copy, seeded once the server's own copy loads — never
  // silently overwritten by a background refetch while there are
  // unsaved edits (`slots !== null` once the caller has touched anything,
  // including a first successful load).
  useEffect(() => {
    if (data && slots === null) setSlots(data.slots)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  const working = slots ?? []
  const indexed = withIndices(working)
  const byDay = groupByDay(indexed)

  function updateSlots(next: AvailabilitySlot[]) {
    setSlots(next)
    setDayErrors({})
  }

  function handleAdd(dayOfWeek: number) {
    updateSlots([...working, { day_of_week: dayOfWeek, start_minute: 540, end_minute: 600 }])
  }

  function handleRemove(absoluteIndex: number) {
    updateSlots(working.filter((_, i) => i !== absoluteIndex))
  }

  function handleChangeStart(absoluteIndex: number, value: number) {
    updateSlots(
      working.map((slot, i) => (i === absoluteIndex ? { ...slot, start_minute: value } : slot)),
    )
  }

  function handleChangeEnd(absoluteIndex: number, value: number) {
    updateSlots(
      working.map((slot, i) => (i === absoluteIndex ? { ...slot, end_minute: value } : slot)),
    )
  }

  function handleSave() {
    const errors = computeDayErrors(working)
    if (Object.keys(errors).length > 0) {
      setDayErrors(errors)
      return
    }
    setDayErrors({})
    save.mutate(
      { slots: working },
      {
        onSuccess: (saved) => setSlots(saved.slots),
        onError: (error) => setDayErrors(dayErrorsFromApiError(error)),
      },
    )
  }

  function handleClear() {
    clear.mutate(undefined, {
      onSuccess: () => {
        setSlots([])
        setDayErrors({})
      },
    })
  }

  if (isLoading) return <p className="text-muted-foreground text-body">Loading…</p>
  if (isError) return <p className="text-destructive text-body">Could not load this week.</p>

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-md border border-input">
        {Array.from({ length: DAYS_IN_WEEK }, (_, dayOfWeek) => (
          <DayRangesField
            key={dayOfWeek}
            dayOfWeek={dayOfWeek}
            dayLabel={dayName(dayOfWeek)}
            ranges={byDay.get(dayOfWeek) ?? []}
            error={dayErrors[dayOfWeek]}
            onAdd={() => handleAdd(dayOfWeek)}
            onRemove={handleRemove}
            onChangeStart={handleChangeStart}
            onChangeEnd={handleChangeEnd}
          />
        ))}
      </div>

      <div className="flex items-center gap-3">
        <Button type="button" onClick={handleSave} disabled={save.isPending}>
          {save.isPending ? 'Saving…' : 'Save'}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={handleClear}
          disabled={clear.isPending || working.length === 0}
        >
          Clear all times
        </Button>
      </div>
    </div>
  )
}
