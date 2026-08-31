import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRouter,
} from '@tanstack/react-router'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { CoachRosterTable } from '@/features/trainer/coaches/ui/coach-roster-table'
import type { TrainerCoachPage, TrainerCoachSummary } from '@/shared/api/types'

import { server } from '../../msw-server'

function coach(overrides: Partial<TrainerCoachSummary> = {}): TrainerCoachSummary {
  return {
    user_id: 'coach-1',
    first_name: 'Ravi',
    last_name: 'Roster',
    email: 'ravi@example.org',
    status: 'active',
    photo_url: null,
    joined_at: '2026-01-01T00:00:00Z',
    availability: [],
    availability_updated_at: null,
    ...overrides,
  }
}

function mockRoster(page: TrainerCoachPage) {
  server.use(http.get('/api/v1/trainer/coaches', () => HttpResponse.json(page)))
}

function renderTable() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  // A minimal one-route tree, rather than the app's full `routeTree` — this
  // test exercises `CoachRosterTable` in isolation, and the only thing it
  // needs from the router is a context for the coach-name `<Link>` to
  // `/trainer/coaches/$coachUserId` (T611).
  const rootRoute = createRootRoute({ component: CoachRosterTable })
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: ['/'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('CoachRosterTable', () => {
  it('shows an empty state when the roster has no coaches', async () => {
    mockRoster({ items: [], total: 0, page: 1, page_size: 25 })

    renderTable()

    expect(
      await screen.findByText('No coaches yet. Invite one above to get started.'),
    ).toBeInTheDocument()
  })

  it('lists a coach with name, email, and joined date', async () => {
    mockRoster({ items: [coach()], total: 1, page: 1, page_size: 25 })

    renderTable()

    expect(await screen.findByText('Ravi Roster')).toBeInTheDocument()
    expect(screen.getByText('ravi@example.org')).toBeInTheDocument()
  })

  it('ends an assignment through the confirmation dialog', async () => {
    mockRoster({ items: [coach()], total: 1, page: 1, page_size: 25 })
    let endedCoachId: string | null = null
    server.use(
      http.delete('/api/v1/trainer/coaches/:coachUserId', ({ params }) => {
        endedCoachId = params.coachUserId as string
        return new HttpResponse(null, { status: 204 })
      }),
    )

    renderTable()
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /end assignment/i }))
    const dialog = await screen.findByRole('alertdialog')
    await user.click(within(dialog).getByRole('button', { name: /end assignment/i }))

    await waitFor(() => expect(endedCoachId).toBe('coach-1'))
  })
})
