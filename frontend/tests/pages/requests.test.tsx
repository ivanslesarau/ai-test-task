import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { ApprovalRequest, ApprovalRequestPage } from '@/shared/api/types'
import { Toaster } from '@/shared/ui/sonner'

import { server } from '../msw-server'

function mockChildSession() {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-child-1',
        email: 'charlie@example.org',
        role: 'player_parent',
        status: 'active',
        first_name: 'Charlie',
        last_name: 'Parent',
        photo_url: null,
        active_player_profile_id: null,
        active_trainer_id: null,
        context_count: 0,
        is_child_account: true,
        portal_branding: { logo_url: null, primary_color: null, updated_at: null },
      }),
    ),
  )
}

const DENIED_REQUEST: ApprovalRequest = {
  id: 'request-denied',
  player_profile_id: 'profile-child',
  player_display_name: 'Charlie Parent',
  kind: 'join_trainer',
  status: 'denied',
  trainer_id: 'trainer-1',
  trainer_display_name: 'Elite Basketball Academy',
  amount_minor: null,
  currency: null,
  requested_at: '2026-01-01T00:00:00Z',
  expires_at: '2026-01-03T00:00:00Z',
  parent_note: 'Not this season.',
  child_note: null,
  resolved_at: '2026-01-02T00:00:00Z',
  resolved_by: 'parent',
}

const PENDING_REQUEST: ApprovalRequest = {
  ...DENIED_REQUEST,
  id: 'request-pending',
  status: 'pending_parent_approval',
  parent_note: null,
  resolved_at: null,
  resolved_by: null,
}

function mockRaisedRequests(items: ApprovalRequest[]) {
  server.use(
    http.get('/api/v1/me/requests', () =>
      HttpResponse.json({
        items,
        page: 1,
        page_size: 25,
        total: items.length,
      } satisfies ApprovalRequestPage),
    ),
  )
}

function renderRequestsPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: ['/requests'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster />
    </QueryClientProvider>,
  )
}

describe('RequestsPage — a child’s own view of what they raised', () => {
  it('shows their own requests, statuses, and the parent’s note on a denial', async () => {
    mockChildSession()
    mockRaisedRequests([DENIED_REQUEST])

    renderRequestsPage()

    expect(await screen.findByText(/Join Elite Basketball Academy/)).toBeInTheDocument()
    expect(screen.getByText('Denied')).toBeInTheDocument()
    expect(screen.getByText('Not this season.')).toBeInTheDocument()
  })

  it('can withdraw a pending request', async () => {
    mockChildSession()
    mockRaisedRequests([PENDING_REQUEST])
    let withdrawCalled = false
    server.use(
      http.post('/api/v1/me/requests/:requestId/withdraw', () => {
        withdrawCalled = true
        return HttpResponse.json({ ...PENDING_REQUEST, status: 'withdrawn' })
      }),
    )

    renderRequestsPage()

    const withdrawButton = await screen.findByRole('button', { name: /withdraw/i })
    await userEvent.click(withdrawButton)

    expect(await screen.findByText(/^withdrawn$/i)).toBeInTheDocument()
    expect(withdrawCalled).toBe(true)
  })

  it('shows the empty state when nothing has been raised', async () => {
    mockChildSession()
    mockRaisedRequests([])

    renderRequestsPage()

    expect(await screen.findByText(/haven.t asked for anything yet/i)).toBeInTheDocument()
  })
})
