import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { AvailabilityWeekEditor } from '@/features/availability/ui/availability-week-editor'
import type { AvailabilityWeek } from '@/shared/api/types'

import { server } from '../../msw-server'

function renderEditor() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <AvailabilityWeekEditor subject={{ kind: 'own' }} />
    </QueryClientProvider>,
  )
  return queryClient
}

function mockGet(week: AvailabilityWeek) {
  server.use(http.get('/api/v1/me/availability', () => HttpResponse.json(week)))
}

describe('AvailabilityWeekEditor', () => {
  it('renders every day of the week with no ranges for a never-stated week', async () => {
    mockGet({ slots: [], updated_at: null })

    renderEditor()

    expect(await screen.findByText('Monday')).toBeInTheDocument()
    expect(screen.getByText('Sunday')).toBeInTheDocument()
    expect(screen.getAllByText('No ranges stated.')).toHaveLength(7)
  })

  it('renders an existing range under the right day', async () => {
    mockGet({
      slots: [{ day_of_week: 2, start_minute: 540, end_minute: 600 }],
      updated_at: '2026-08-20T00:00:00Z',
    })

    renderEditor()

    await screen.findByText('Wednesday')
    // Six of the seven days have no ranges; Wednesday holds the one slot.
    expect(screen.getAllByText('No ranges stated.')).toHaveLength(6)
  })

  it('adds a range to a day and saves the whole week', async () => {
    mockGet({ slots: [], updated_at: null })
    let savedBody: unknown = null
    server.use(
      http.put('/api/v1/me/availability', async ({ request }) => {
        savedBody = await request.json()
        return HttpResponse.json({
          slots: [{ day_of_week: 0, start_minute: 540, end_minute: 600 }],
          updated_at: '2026-08-28T12:00:00Z',
        } satisfies AvailabilityWeek)
      }),
    )

    renderEditor()
    await screen.findByText('Monday')

    const addButtons = screen.getAllByRole('button', { name: 'Add range' })
    const mondayAddButton = addButtons[0]
    expect(mondayAddButton).toBeDefined()
    if (mondayAddButton) await userEvent.click(mondayAddButton)

    const saveButton = screen.getByRole('button', { name: /save/i })
    await userEvent.click(saveButton)

    await waitFor(() => {
      expect(savedBody).toEqual({
        slots: [{ day_of_week: 0, start_minute: 540, end_minute: 600 }],
      })
    })
  })

  it('shows the server refusal under the offending day and changes nothing else', async () => {
    mockGet({ slots: [], updated_at: null })
    server.use(
      http.put(
        '/api/v1/me/availability',
        () =>
          HttpResponse.json(
            {
              error: {
                code: 'validation_failed',
                message: 'One or more fields are invalid.',
                fields: [{ field: '0', message: 'Ranges on this day overlap.' }],
              },
            },
            { status: 422 },
          ),
        { once: true },
      ),
    )

    renderEditor()
    await screen.findByText('Monday')

    const addButtons = screen.getAllByRole('button', { name: 'Add range' })
    const mondayAddButton = addButtons[0]
    if (mondayAddButton) await userEvent.click(mondayAddButton)
    await userEvent.click(screen.getByRole('button', { name: /save/i }))

    expect(await screen.findByText('Ranges on this day overlap.')).toBeInTheDocument()
  })

  it('clears the week and reflects the cleared state', async () => {
    mockGet({
      slots: [{ day_of_week: 3, start_minute: 540, end_minute: 600 }],
      updated_at: '2026-08-01T00:00:00Z',
    })
    server.use(http.delete('/api/v1/me/availability', () => new HttpResponse(null, { status: 204 })))

    renderEditor()
    await screen.findByText('Thursday')

    const clearButton = await screen.findByRole('button', { name: /clear all times/i })
    await userEvent.click(clearButton)

    await waitFor(() => {
      expect(screen.getAllByText('No ranges stated.')).toHaveLength(7)
    })
  })
})
