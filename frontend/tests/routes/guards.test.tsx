import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'

import { server } from '../msw-server'

function renderAt(initialPath: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [initialPath] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

describe('route guards', () => {
  it('redirects an unauthenticated visitor from a protected route to /login', async () => {
    server.use(
      http.get('/api/v1/auth/session', () =>
        HttpResponse.json(
          { error: { code: 'not_authenticated', message: 'Sign in to continue.' } },
          { status: 401 },
        ),
      ),
    )

    const router = renderAt('/profile')

    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(router.state.location.search).toMatchObject({ redirect: '/profile' })
  })

  it('shows the forbidden view rather than redirecting when a Trainer visits an admin route', async () => {
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

    const router = renderAt('/admin/users')

    expect(await screen.findByText(/don't have access/i)).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/admin/users')
  })

  it('renders the admin page for a Super Admin without a forbidden message', async () => {
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

    renderAt('/admin/users')

    expect(await screen.findByText('Users')).toBeInTheDocument()
    expect(screen.queryByText(/don't have access/i)).not.toBeInTheDocument()
  })
})
