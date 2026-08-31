import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { CoachInvitationPage, CurrentUser, TrainerCoachPage } from '@/shared/api/types'

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

function mockInvitations(page: CoachInvitationPage) {
  server.use(http.get('/api/v1/trainer/coach-invitations', () => HttpResponse.json(page)))
}

function mockCoaches(page: TrainerCoachPage) {
  server.use(http.get('/api/v1/trainer/coaches', () => HttpResponse.json(page)))
}

function renderTrainerCoaches() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: ['/trainer/coaches'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('TrainerCoachesPage', () => {
  it('a trainer reaches the page and sees the roster, invite form, and list', async () => {
    mockSession('trainer')
    mockInvitations({ items: [], total: 0, page: 1, page_size: 25 })
    mockCoaches({ items: [], total: 0, page: 1, page_size: 25 })

    renderTrainerCoaches()

    expect(await screen.findByRole('heading', { name: 'Coaches' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Your coaches' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Invite a coach' })).toBeInTheDocument()
    expect(await screen.findByText('No invitations yet.')).toBeInTheDocument()
    expect(
      await screen.findByText('No coaches yet. Invite one above to get started.'),
    ).toBeInTheDocument()
  })

  it('a coach is refused the page', async () => {
    mockSession('coach')

    renderTrainerCoaches()

    expect(await screen.findByText(/restricted to Trainers/i)).toBeInTheDocument()
  })

  it('a player/parent is refused the page', async () => {
    mockSession('player_parent')

    renderTrainerCoaches()

    expect(await screen.findByText(/restricted to Trainers/i)).toBeInTheDocument()
  })
})
