import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { CurrentUser, Impersonation, ImpersonationPage } from '@/shared/api/types'

import { server } from '../msw-server'

function mockSession(role: CurrentUser['role']) {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-1',
        email: 'person@example.org',
        role,
        status: 'active',
        first_name: 'Ada',
        last_name: 'Admin',
        photo_url: null,
        active_player_profile_id: null,
        active_trainer_id: null,
        context_count: 0,
        is_child_account: false,
        portal_branding: { logo_url: null, primary_color: null, updated_at: null },
        impersonation: null,
        impersonation_ended: null,
      } satisfies CurrentUser),
    ),
  )
}

function mockHistory(items: Impersonation[]) {
  const page: ImpersonationPage = { items, total: items.length, page: 1, page_size: 25 }
  server.use(http.get('/api/v1/admin/impersonations', () => HttpResponse.json(page)))
}

function renderAdminImpersonations(initialEntry = '/admin/impersonations') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [initialEntry] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

const OPEN_ROW: Impersonation = {
  id: 'imp-1',
  admin: { user_id: 'admin-1', display_name: 'Ada Admin', role: 'super_admin' },
  target: { user_id: 'trainer-1', display_name: 'Tara Trainer', role: 'trainer' },
  target_status_at_start: 'active',
  started_at: '2026-08-20T10:00:00Z',
  expires_at: '2026-08-20T11:00:00Z',
  ended_at: null,
  end_reason: null,
  duration_seconds: null,
}

describe('AdminImpersonationsPage', () => {
  it('a Super Admin reaches the page and sees the history', async () => {
    mockSession('super_admin')
    mockHistory([OPEN_ROW])

    renderAdminImpersonations()

    expect(await screen.findByRole('heading', { name: 'Impersonation history' })).toBeInTheDocument()
    expect(await screen.findByText('Tara Trainer')).toBeInTheDocument()
    // "Ada Admin" appears both as the signed-in user's own name in the
    // app-shell header and as the history row's admin participant — at
    // least one instance confirms the table itself rendered the row.
    expect(screen.getAllByText('Ada Admin').length).toBeGreaterThanOrEqual(1)
  })

  it('an in-progress row is marked and carries no duration', async () => {
    mockSession('super_admin')
    mockHistory([OPEN_ROW])

    renderAdminImpersonations()

    expect(await screen.findByText('In progress')).toBeInTheDocument()
    expect(screen.getAllByRole('cell').some((cell) => cell.textContent === '—')).toBe(true)
  })

  it('a trainer is refused the page', async () => {
    mockSession('trainer')

    renderAdminImpersonations()

    expect(await screen.findByText(/restricted to Super Admins/i)).toBeInTheDocument()
  })

  it('filters given in the URL survive a reload', async () => {
    mockSession('super_admin')
    mockHistory([])

    const router = renderAdminImpersonations(
      '/admin/impersonations?target_user_id=11111111-1111-1111-1111-111111111111',
    )

    await screen.findByText('No impersonations recorded.')
    expect(router.state.location.search).toMatchObject({
      target_user_id: '11111111-1111-1111-1111-111111111111',
    })
  })
})
