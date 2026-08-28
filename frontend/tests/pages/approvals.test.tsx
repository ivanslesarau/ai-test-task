import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { ApprovalRequest, ApprovalRequestPage } from '@/shared/api/types'
import { Toaster } from '@/shared/ui/sonner'

import { server } from '../msw-server'

function mockParentSession() {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-parent-1',
        email: 'parent@example.org',
        role: 'player_parent',
        status: 'active',
        first_name: 'Pat',
        last_name: 'Parent',
        photo_url: null,
        active_player_profile_id: null,
        active_trainer_id: null,
        context_count: 0,
        is_child_account: false,
        portal_branding: { logo_url: null, primary_color: null, updated_at: null },
      }),
    ),
  )
}

// A generous window in the future — the countdown must not disable the
// controls while time remains (contracts/frontend-contracts.md §18).
const FAR_FUTURE = new Date(Date.now() + 47 * 60 * 60 * 1000).toISOString()

const PENDING_REQUEST: ApprovalRequest = {
  id: 'request-1',
  player_profile_id: 'profile-child',
  player_display_name: 'Charlie Parent',
  kind: 'join_trainer',
  status: 'pending_parent_approval',
  trainer_id: 'trainer-1',
  trainer_display_name: 'Elite Basketball Academy',
  amount_minor: null,
  currency: null,
  requested_at: '2026-01-01T00:00:00Z',
  expires_at: FAR_FUTURE,
  parent_note: null,
  child_note: null,
  resolved_at: null,
  resolved_by: null,
}

function mockApprovalsQueue(items: ApprovalRequest[]) {
  server.use(
    http.get('/api/v1/me/approvals', () =>
      HttpResponse.json({
        items,
        page: 1,
        page_size: 25,
        total: items.length,
      } satisfies ApprovalRequestPage),
    ),
  )
}

function renderApprovalsPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: ['/approvals'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster />
    </QueryClientProvider>,
  )
}

describe('ApprovalsPage — the parent decision queue', () => {
  it('shows the child, subject, amount, and time remaining', async () => {
    mockParentSession()
    mockApprovalsQueue([PENDING_REQUEST])

    renderApprovalsPage()

    expect(await screen.findByText('Charlie Parent')).toBeInTheDocument()
    expect(screen.getByText(/Join Elite Basketball Academy/)).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.getByText(/h left/)).toBeInTheDocument()
  })

  it('shows an empty state when nothing is pending', async () => {
    mockParentSession()
    mockApprovalsQueue([])

    renderApprovalsPage()

    expect(await screen.findByText(/nothing is waiting on your decision/i)).toBeInTheDocument()
  })

  it('the derived countdown does not disable the controls', async () => {
    mockParentSession()
    mockApprovalsQueue([PENDING_REQUEST])

    renderApprovalsPage()

    const approveButton = await screen.findByRole('button', { name: /^approve$/i })
    expect(approveButton).toBeEnabled()
    expect(screen.getByRole('button', { name: /^deny$/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /ask a question/i })).toBeEnabled()
  })

  it('approving posts to the approve endpoint and shows a success toast', async () => {
    mockParentSession()
    mockApprovalsQueue([PENDING_REQUEST])
    server.use(
      http.post('/api/v1/me/approvals/:requestId/approve', () =>
        HttpResponse.json({ ...PENDING_REQUEST, status: 'approved' }),
      ),
    )

    renderApprovalsPage()

    const approveButton = await screen.findByRole('button', { name: /^approve$/i })
    await userEvent.click(approveButton)

    expect(await screen.findByText(/approved/i)).toBeInTheDocument()
  })

  it('denying with a note posts the note', async () => {
    mockParentSession()
    mockApprovalsQueue([PENDING_REQUEST])
    let capturedBody: unknown
    server.use(
      http.post('/api/v1/me/approvals/:requestId/deny', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({ ...PENDING_REQUEST, status: 'denied' })
      }),
    )

    renderApprovalsPage()

    await userEvent.click(await screen.findByRole('button', { name: /^deny$/i }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.type(within(dialog).getByLabelText(/note/i), 'Not this season.')
    await userEvent.click(within(dialog).getByRole('button', { name: /^deny$/i }))

    expect(await screen.findByText(/denied/i)).toBeInTheDocument()
    expect(capturedBody).toEqual({ note: 'Not this season.' })
  })

  it('a 409 refreshes the queue instead of showing an error', async () => {
    mockParentSession()
    mockApprovalsQueue([PENDING_REQUEST])
    server.use(
      http.post('/api/v1/me/approvals/:requestId/approve', () =>
        HttpResponse.json(
          { error: { code: 'request_already_resolved', message: 'Already decided.' } },
          { status: 409 },
        ),
      ),
    )

    renderApprovalsPage()

    const approveButton = await screen.findByRole('button', { name: /^approve$/i })
    await userEvent.click(approveButton)

    expect(await screen.findByText(/already decided/i)).toBeInTheDocument()
    expect(screen.queryByText(/could not approve/i)).not.toBeInTheDocument()
  })
})
