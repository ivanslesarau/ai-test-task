import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { AvailabilityWeek, CurrentUser } from '@/shared/api/types'

import { server } from '../msw-server'

function mockSession(role: CurrentUser['role']) {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-1',
        email: 'person@example.org',
        role,
        status: 'active',
        first_name: 'Cody',
        last_name: 'Coach',
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

function mockAvailability(week: AvailabilityWeek) {
  server.use(http.get('/api/v1/me/availability', () => HttpResponse.json(week)))
}

function renderMyTimes() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: ['/my-times'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('MyTimesPage', () => {
  it('a coach reaches the page and sees the week editor', async () => {
    mockSession('coach')
    mockAvailability({ slots: [], updated_at: null })

    renderMyTimes()

    expect(await screen.findByRole('heading', { name: 'My Times' })).toBeInTheDocument()
    expect(await screen.findByText('Monday')).toBeInTheDocument()
  })

  it('a non-coach is refused the page', async () => {
    mockSession('trainer')

    renderMyTimes()

    expect(await screen.findByText(/restricted to Coaches/i)).toBeInTheDocument()
  })
})
