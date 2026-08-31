import { formatClock } from '@/entities/availability/model/format-summary'
import {
  MAX_SLOTS_PER_DAY,
  MINUTES_IN_DAY,
  MINUTES_PER_SLOT_STEP,
} from '@/entities/availability/model/week'
import { Button } from '@/shared/ui/button'
import { FormMessage } from '@/shared/ui/form-field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'

const START_OPTIONS = Array.from(
  { length: MINUTES_IN_DAY / MINUTES_PER_SLOT_STEP },
  (_, i) => i * MINUTES_PER_SLOT_STEP,
)
const END_OPTIONS = Array.from(
  { length: MINUTES_IN_DAY / MINUTES_PER_SLOT_STEP },
  (_, i) => (i + 1) * MINUTES_PER_SLOT_STEP,
)

export interface DayRangeRow {
  /** The range's index within the whole week's flat `slots` array — what
   * `onChange`/`onRemove` address, so the editor never has to re-derive
   * it from the day-grouped view. */
  absoluteIndex: number
  start_minute: number
  end_minute: number
}

interface DayRangesFieldProps {
  dayOfWeek: number
  dayLabel: string
  ranges: DayRangeRow[]
  /** The set-level error for this day alone (FR-027) — from either the
   * client-side validator or the server's day-keyed 422, mapped onto the
   * right day by the caller (frontend-contracts.md §32). */
  error?: string
  onAdd: () => void
  onRemove: (absoluteIndex: number) => void
  onChangeStart: (absoluteIndex: number, value: number) => void
  onChangeEnd: (absoluteIndex: number, value: number) => void
}

/** One day's ranges — add/remove rows and a quarter-hour picker for each
 * boundary (FR-026, FR-028). Owner-agnostic: used identically by the
 * coach's My Times editor and the family's Availability editor
 * (frontend-contracts.md §34). */
export function DayRangesField({
  dayOfWeek,
  dayLabel,
  ranges,
  error,
  onAdd,
  onRemove,
  onChangeStart,
  onChangeEnd,
}: DayRangesFieldProps) {
  return (
    <div className="flex flex-col gap-2 border-b border-input py-3 last:border-b-0">
      <div className="flex items-center justify-between">
        <span className="text-body font-medium">{dayLabel}</span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onAdd}
          disabled={ranges.length >= MAX_SLOTS_PER_DAY}
        >
          Add range
        </Button>
      </div>

      {ranges.length === 0 && (
        <p className="text-muted-foreground text-caption">No ranges stated.</p>
      )}

      {ranges.map((range) => (
        <div key={range.absoluteIndex} className="flex items-center gap-2">
          <Select
            value={String(range.start_minute)}
            onValueChange={(value) => onChangeStart(range.absoluteIndex, Number(value))}
          >
            <SelectTrigger aria-label={`${dayLabel} start time`} className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {START_OPTIONS.map((minute) => (
                <SelectItem key={minute} value={String(minute)}>
                  {formatClock(minute)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span aria-hidden="true">–</span>
          <Select
            value={String(range.end_minute)}
            onValueChange={(value) => onChangeEnd(range.absoluteIndex, Number(value))}
          >
            <SelectTrigger aria-label={`${dayLabel} end time`} className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {END_OPTIONS.map((minute) => (
                <SelectItem key={minute} value={String(minute)}>
                  {formatClock(minute)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onRemove(range.absoluteIndex)}
            aria-label={`Remove this ${dayLabel} range`}
          >
            Remove
          </Button>
        </div>
      ))}

      {error && <FormMessage>{error}</FormMessage>}
      <span className="sr-only">day index {dayOfWeek}</span>
    </div>
  )
}
