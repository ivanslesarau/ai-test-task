import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'

import { server } from '../msw-server'

function renderDashboard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: ['/'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

function mockSuperAdminSession() {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-super-admin-1',
        email: 'admin@example.org',
        role: 'super_admin',
        status: 'active',
        first_name: 'Ada',
        last_name: 'Admin',
        photo_url: null,
      }),
    ),
  )
}

function mockTrainerSession() {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-trainer-1',
        email: 'trainer@example.org',
        role: 'trainer',
        status: 'active',
        first_name: 'Tara',
        last_name: 'Trainer',
        photo_url: null,
      }),
    ),
  )
}

function mockPlayerParentSession(overrides: Record<string, unknown> = {}) {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-player-1',
        email: 'player@example.org',
        role: 'player_parent',
        status: 'active',
        first_name: 'Pat',
        last_name: 'Player',
        photo_url: null,
        active_player_profile_id: null,
        active_trainer_id: null,
        context_count: 0,
        is_child_account: false,
        ...overrides,
      }),
    ),
    http.get('/api/v1/me/contexts', () =>
      HttpResponse.json({
        active_player_profile_id:
          (overrides.active_player_profile_id as string | null | undefined) ?? null,
        active_trainer_id: (overrides.active_trainer_id as string | null | undefined) ?? null,
        contexts:
          overrides.context_count === 1
            ? [
                {
                  player_profile_id: 'profile-a',
                  player_display_name: 'Pat Player',
                  player_profile_kind: 'self',
                  trainer_id: 'trainer-a',
                  trainer_display_name: 'Elite Basketball Academy',
                  branding: { logo_url: null, primary_color: null, updated_at: null },
                  joined_at: '2026-01-01T00:00:00Z',
                },
              ]
            : [],
      }),
    ),
  )
}

describe('DashboardPage — per-role landing content', () => {
  it('shows the user directory link for a Super Admin', async () => {
    mockSuperAdminSession()
    renderDashboard()

    const link = await screen.findByRole('link', { name: /go to the user directory/i })
    expect(link).toHaveAttribute('href', '/admin/users')
  })

  it('shows both trainer entries — Portal settings and Players — for a Trainer', async () => {
    mockTrainerSession()
    renderDashboard()

    await screen.findByText('Tara Trainer')

    // The header's PrimaryNav (T302/T303) renders the same two labels, so
    // the landing area's own copy is the *second* match for each — proof
    // the dashboard reads T301's descriptors independently of the shell
    // rather than the header being the only entry point (FR-019, fix
    // F7/T306).
    const portalLinks = screen.getAllByRole('link', { name: 'Portal settings' })
    const playersLinks = screen.getAllByRole('link', { name: 'Players' })
    expect(portalLinks).toHaveLength(2)
    expect(playersLinks).toHaveLength(2)
    portalLinks.forEach((link) => expect(link).toHaveAttribute('href', '/trainer/portal'))
    playersLinks.forEach((link) => expect(link).toHaveAttribute('href', '/trainer/players'))
  })

  it('shows the zero-trainer empty state for an unassociated player', async () => {
    mockPlayerParentSession({ context_count: 0, active_trainer_id: null })
    renderDashboard()

    expect(
      await screen.findByText(/not currently connected to a trainer/i),
    ).toBeInTheDocument()
  })

  it("shows the active trainer's name for a player connected to exactly one", async () => {
    mockPlayerParentSession({
      context_count: 1,
      active_player_profile_id: 'profile-a',
      active_trainer_id: 'trainer-a',
    })
    renderDashboard()

    expect(await screen.findByText('Elite Basketball Academy')).toBeInTheDocument()
  })
})
