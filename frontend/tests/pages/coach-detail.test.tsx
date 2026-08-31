import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { CurrentUser, TrainerCoachPage, TrainerCoachSummary } from '@/shared/api/types'

import { server } from '../msw-server'

function mockSession(role: CurrentUser['role']) {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-1',
        email: 'person@example.org',
        role,
        status: 'active',
        first_name: 'Tara',
        last_name: 'Trainer',
        photo_url: null,
        active_player_profile_id: null,
        active_trainer_id: null,
        context_count: 0,
        is_child_account: false,
        portal_branding: { logo_url: null, primary_color: null, updated_at: null },
      } satisfies CurrentUser),
    ),
  )
}

function mockCoaches(items: TrainerCoachSummary[]) {
  const page: TrainerCoachPage = { items, total: items.length, page: 1, page_size: 100 }
  server.use(http.get('/api/v1/trainer/coaches', () => HttpResponse.json(page)))
}

function renderCoachDetail(coachUserId: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [`/trainer/coaches/${coachUserId}`] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

const BASE_COACH: TrainerCoachSummary = {
  user_id: 'coach-1',
  first_name: 'Cody',
  last_name: 'Coach',
  email: 'cody@example.org',
  status: 'active',
  photo_url: null,
  joined_at: '2026-08-01T00:00:00Z',
  availability: [],
  availability_updated_at: null,
}

describe('CoachDetailPage', () => {
  it("renders the coach's identity and 'No times set' for an unstated week", async () => {
    mockSession('trainer')
    mockCoaches([BASE_COACH])

    renderCoachDetail('coach-1')

    expect(await screen.findByRole('heading', { name: 'Cody Coach' })).toBeInTheDocument()
    expect(screen.getByText('cody@example.org')).toBeInTheDocument()
    expect(screen.getByText('No times set')).toBeInTheDocument()
  })

  it("renders the coach's stated week and a stale revision date", async () => {
    mockSession('trainer')
    mockCoaches([
      {
        ...BASE_COACH,
        availability: [{ day_of_week: 0, start_minute: 1020, end_minute: 1200 }],
        availability_updated_at: '2020-01-01T00:00:00Z',
      },
    ])

    renderCoachDetail('coach-1')

    expect(await screen.findByText('Monday')).toBeInTheDocument()
    expect(screen.getByText('5pm–8pm')).toBeInTheDocument()
    expect(screen.getByText(/Last revised/)).toBeInTheDocument()
  })

  it('offers no control anywhere that would edit the coach’s own times', async () => {
    mockSession('trainer')
    mockCoaches([
      {
        ...BASE_COACH,
        availability: [{ day_of_week: 0, start_minute: 1020, end_minute: 1200 }],
        availability_updated_at: '2026-08-20T00:00:00Z',
      },
    ])

    renderCoachDetail('coach-1')

    await screen.findByRole('heading', { name: 'Cody Coach' })
    expect(screen.queryByRole('button', { name: /save/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /clear/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
  })

  it('a coach not on this page of the roster reads as an error rather than another coach’s data', async () => {
    mockSession('trainer')
    mockCoaches([])

    renderCoachDetail('missing-coach')

    expect(await screen.findByText('Could not load this coach.')).toBeInTheDocument()
  })
})
