import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'

import { server } from '../msw-server'

const DEFAULT_BRANDING = { logo_url: null, primary_color: null, updated_at: null }

function renderJoinPage(code: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [`/join/${code}`] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

function mockPreview(state: string, trainerName = 'Acme Academy') {
  server.use(
    http.get('/api/v1/join/:code', () =>
      HttpResponse.json({
        trainer_display_name: trainerName,
        branding: DEFAULT_BRANDING,
        viewer: { state },
      }),
    ),
  )
}

describe('JoinPage — the four viewer.state branches', () => {
  it('shows the registration form only for "anonymous"', async () => {
    mockPreview('anonymous')
    renderJoinPage('abc123')

    expect(await screen.findByLabelText(/first name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^join acme academy$/i })).not.toBeInTheDocument()
  })

  it('shows a single confirm button for "can_join", not a registration form', async () => {
    mockPreview('can_join')
    renderJoinPage('abc123')

    expect(await screen.findByRole('button', { name: /join acme academy/i })).toBeInTheDocument()
    expect(screen.queryByLabelText(/first name/i)).not.toBeInTheDocument()
  })

  it('tells an already-associated visitor they are connected, with no form or confirm button', async () => {
    mockPreview('already_associated')
    renderJoinPage('abc123')

    expect(await screen.findByText(/you already train with acme academy/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/first name/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^join acme academy$/i })).not.toBeInTheDocument()
  })

  it('explains the link is for players and parents for "role_cannot_join"', async () => {
    mockPreview('role_cannot_join')
    renderJoinPage('abc123')

    expect(await screen.findByText(/this link is for players and parents/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/first name/i)).not.toBeInTheDocument()
  })

  it('shows a single not-valid message for an unknown code, naming no trainer', async () => {
    server.use(
      http.get('/api/v1/join/:code', () =>
        HttpResponse.json(
          { error: { code: 'invitation_link_invalid', message: 'This link is no longer valid.' } },
          { status: 404 },
        ),
      ),
    )
    renderJoinPage('not-a-real-code')

    expect(await screen.findByText(/this link is no longer valid/i)).toBeInTheDocument()
  })

  it('reaches the join route even without a session cookie set', async () => {
    // No /auth/session mock override needed at all — the public join
    // route never calls it (research.md R-25, frontend-contracts.md §8).
    mockPreview('anonymous')
    const router = renderJoinPage('abc123')

    await waitFor(() => expect(router.state.location.pathname).toBe('/join/abc123'))
  })
})
