import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { userKeys } from '@/entities/user/api/query-keys'
import { routeTree } from '@/routeTree.gen'
import type { CurrentUser, Impersonation, UserPage } from '@/shared/api/types'

import { fixtures } from '../../msw-handlers'
import { server } from '../../msw-server'

const IMPERSONATION: Impersonation = {
  id: 'impersonation-1',
  admin: { user_id: 'user-super-admin-1', display_name: 'Ada Admin', role: 'super_admin' },
  target: { user_id: 'user-trainer-1', display_name: 'Tara Trainer', role: 'trainer' },
  target_status_at_start: 'active',
  started_at: '2026-01-01T00:00:00Z',
  expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
  ended_at: null,
  end_reason: null,
  duration_seconds: null,
}

function directoryPage(): UserPage {
  return { items: [fixtures.userDetail], page: 1, page_size: 25, total: 1 }
}

// A full app render plus a network round trip can occasionally exceed
// Testing Library's 1s default under the full suite's parallel load; these
// assertions wait for exactly that on first mount.
const LONG_TIMEOUT = { timeout: 5000 }

function renderAt(initialPath: string, queryClient: QueryClient) {
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
}

describe('starting an impersonation', () => {
  it('clears the whole query cache before landing on the impersonated portal', async () => {
    server.use(http.get('/api/v1/admin/users', () => HttpResponse.json(directoryPage())))
    // The impersonated portal (index route) describes the target.
    let impersonating = false
    server.use(
      http.get('/api/v1/auth/session', () =>
        HttpResponse.json(
          impersonating
            ? ({
                ...fixtures.superAdmin,
                id: fixtures.userDetail.id,
                role: 'trainer',
                impersonation: IMPERSONATION,
              } satisfies CurrentUser)
            : fixtures.superAdmin,
        ),
      ),
    )
    server.use(
      http.post('/api/v1/admin/impersonations', () => {
        impersonating = true
        return HttpResponse.json(IMPERSONATION, { status: 201 })
      }),
    )

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    renderAt('/admin/users', queryClient)

    await screen.findByRole('table', {}, LONG_TIMEOUT)
    // A directory page is cached — this is the Super Admin's own data,
    // which must not survive into the impersonated portal.
    expect(
      queryClient.getQueryCache().findAll({ queryKey: userKeys.all }).length,
    ).toBeGreaterThan(0)

    await userEvent.click(screen.getByRole('button', { name: /impersonate/i }))
    await userEvent.click(await screen.findByRole('button', { name: /start impersonating/i }))

    // Cleared as part of the mutation's own onSuccess (frontend-contracts.md
    // §35) — nothing belonging to the Super Admin's own portal remains.
    await screen.findByRole('navigation', { name: 'Primary' }, LONG_TIMEOUT)
    expect(queryClient.getQueryCache().findAll({ queryKey: userKeys.all })).toHaveLength(0)
  })
})

describe('ending an impersonation', () => {
  it('clears the whole query cache before returning to the admin their own portal', async () => {
    server.use(
      http.get('/api/v1/auth/session', () =>
        HttpResponse.json({
          ...fixtures.superAdmin,
          id: IMPERSONATION.target.user_id,
          role: 'trainer',
          impersonation: IMPERSONATION,
        } satisfies CurrentUser),
      ),
    )
    server.use(http.delete('/api/v1/admin/impersonations/current', () => new HttpResponse(null, { status: 204 })))

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    renderAt('/', queryClient)

    const exitButton = await screen.findByRole('button', { name: /exit/i }, LONG_TIMEOUT)
    // A query that belongs to the impersonated portal — must not survive
    // the exit any more than the admin's own data may survive impersonating
    // someone else.
    queryClient.setQueryData(['trainer-portal-probe'], { probe: true })
    expect(queryClient.getQueryData(['trainer-portal-probe'])).toBeDefined()

    await userEvent.click(exitButton)

    await screen.findByRole('navigation', { name: 'Primary' }, LONG_TIMEOUT)
    expect(queryClient.getQueryData(['trainer-portal-probe'])).toBeUndefined()
  })
})
