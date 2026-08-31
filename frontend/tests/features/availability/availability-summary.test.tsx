import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AvailabilitySummary } from '@/features/availability/ui/availability-summary'

describe('AvailabilitySummary', () => {
  it('renders "No times set" for a never-stated week, with no date', () => {
    render(<AvailabilitySummary slots={[]} updatedAt={null} />)

    expect(screen.getByText('No times set')).toBeInTheDocument()
    expect(screen.queryByText(/Updated/)).not.toBeInTheDocument()
  })

  it('renders "No times set" for a deliberately-cleared week, never "Unavailable"', () => {
    render(<AvailabilitySummary slots={[]} updatedAt="2026-08-20T00:00:00Z" />)

    expect(screen.getByText('No times set')).toBeInTheDocument()
    expect(screen.queryByText(/Unavailable/)).not.toBeInTheDocument()
  })

  it('renders the formatted summary and the revision date for a stated week', () => {
    render(
      <AvailabilitySummary
        slots={[
          { day_of_week: 0, start_minute: 1020, end_minute: 1200 },
          { day_of_week: 2, start_minute: 1080, end_minute: 1260 },
        ]}
        updatedAt="2026-08-20T00:00:00Z"
      />,
    )

    expect(screen.getByText('Mon 5pm–8pm, Wed 6pm–9pm')).toBeInTheDocument()
    expect(screen.getByText(/Updated/)).toBeInTheDocument()
  })
})
