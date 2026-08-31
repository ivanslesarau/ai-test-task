import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'

import { server } from '../msw-server'

function mockSignedOut() {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json(
        { error: { code: 'not_authenticated', message: 'Sign in to continue.' } },
        { status: 401 },
      ),
    ),
  )
}

function renderRoute(token: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [`/coach-invite/${token}`] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

describe('/coach-invite/$token route', () => {
  it('is reachable without a session (public route)', async () => {
    mockSignedOut()
    server.use(
      http.get('/api/v1/coach-invitations/:token', () =>
        HttpResponse.json({
          invited_email: 'someone@example.org',
          invitee_name: null,
          message: null,
          expires_at: '2026-09-01T00:00:00Z',
          account_exists: false,
          trainer: {
            business_name: 'Reachable FC',
            portal_branding: { logo_url: null, primary_color: null, updated_at: null },
          },
        }),
      ),
    )

    const router = renderRoute('a-real-token')

    expect(await screen.findByRole('heading', { name: /join reachable fc/i })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/coach-invite/a-real-token')
  })

  it('an unusable token renders the single refusal message, not a stack trace', async () => {
    mockSignedOut()
    server.use(
      http.get('/api/v1/coach-invitations/:token', () =>
        HttpResponse.json(
          { error: { code: 'invitation_link_invalid', message: 'This invitation is no longer valid.' } },
          { status: 404 },
        ),
      ),
    )

    renderRoute('not-a-real-token')

    expect(await screen.findByText(/this link is no longer valid/i)).toBeInTheDocument()
    expect(screen.queryByText(/stack|traceback|exception/i)).not.toBeInTheDocument()
  })
})
