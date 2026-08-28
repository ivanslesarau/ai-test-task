import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
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

describe('JoinPage — the child_must_ask_parent viewer state (US11, T386)', () => {
  it('renders the blocked-child branch, with no form and no confirm button', async () => {
    mockPreview('child_must_ask_parent')
    let acceptCalls = 0
    server.use(
      http.post('/api/v1/join/:code/accept', () => {
        acceptCalls += 1
        return HttpResponse.json(
          {
            error: {
              code: 'child_must_ask_parent',
              message: 'Ask your parent to register you with this trainer.',
            },
          },
          { status: 403 },
        )
      }),
    )

    renderJoinPage('abc123')

    expect(
      await screen.findByText(/ask your parent to register you with acme academy/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/we've emailed them about it/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/first name/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^join acme academy$/i })).not.toBeInTheDocument()
    expect(acceptCalls).toBe(1)
  })

  it('tells an already-connected child so, without the blocked-child message', async () => {
    mockPreview('already_associated')
    let acceptCalls = 0
    server.use(
      http.post('/api/v1/join/:code/accept', () => {
        acceptCalls += 1
        return HttpResponse.json({ error: { code: 'never_called', message: '' } }, { status: 500 })
      }),
    )

    renderJoinPage('abc123')

    expect(await screen.findByText(/you already train with acme academy/i)).toBeInTheDocument()
    expect(
      screen.queryByText(/ask your parent to register you with acme academy/i),
    ).not.toBeInTheDocument()
    expect(acceptCalls).toBe(0)
  })
})
