import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'

import { fixtures } from '../msw-handlers'
import { server } from '../msw-server'

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

/** Several pages compose both the shell's own `BackButton` and a
 * page-specific one (T183-T185); either satisfies FR-061 since both are
 * history-based with the same `fallbackTo`. Tests exercise the last one
 * rendered — the page's own, the more specific of the two. */
function getBackButton() {
  const buttons = screen.getAllByRole('button', { name: /back/i })
  return buttons[buttons.length - 1]
}

function renderAt(initialEntries: string[], initialIndex?: number) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries, initialIndex }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

describe('BackButton (via the app shell)', () => {
  it('uses history.back() when there is history to go back to', async () => {
    mockSuperAdminSession()
    const router = renderAt(['/', '/profile'], 1)

    await screen.findByRole('heading', { name: 'My profile' })

    await userEvent.click(getBackButton())

    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
  })

  it('navigates to fallbackTo when there is no history to go back to', async () => {
    mockSuperAdminSession()
    const router = renderAt(['/profile'])

    await screen.findByRole('heading', { name: 'My profile' })

    await userEvent.click(getBackButton())

    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
  })

  it('returning from a user detail restores the directory filters', async () => {
    mockSuperAdminSession()
    server.use(
      http.get('/api/v1/admin/users', () =>
        HttpResponse.json({ items: [fixtures.userDetail], page: 1, page_size: 25, total: 1 }),
      ),
      http.get('/api/v1/admin/users/:userId', () => HttpResponse.json(fixtures.userDetail)),
    )
    const router = renderAt(
      ['/admin/users?role=trainer', `/admin/users/${fixtures.userDetail.id}`],
      1,
    )

    await screen.findByRole('heading', { name: `${fixtures.userDetail.first_name} ${fixtures.userDetail.last_name}` })

    await userEvent.click(getBackButton())

    await waitFor(() => expect(router.state.location.pathname).toBe('/admin/users'))
    expect(router.state.location.search).toMatchObject({ role: 'trainer' })
  })
})
