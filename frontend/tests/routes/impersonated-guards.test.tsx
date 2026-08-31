import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { CurrentUser, Impersonation } from '@/shared/api/types'

import { fixtures } from '../msw-handlers'
import { server } from '../msw-server'

/**
 * US6 (tasks.md T643, FR-043): existing route guards need no
 * impersonation-specific code. `/_authed/admin.tsx`'s `AdminGate` reads
 * `useSession()` exactly as it always has — a session describing a
 * Trainer is refused the same way whether that Trainer is the real
 * signed-in account or the effective identity of a Super Admin mid
 * impersonation (research.md R2-14, frontend-contracts.md §35).
 */
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

function renderAdminUsers(session: CurrentUser) {
  server.use(http.get('/api/v1/auth/session', () => HttpResponse.json(session)))
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: ['/admin/users'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('the existing /admin guard, under impersonation', () => {
  it('redirects an impersonated Trainer away from /admin/users exactly as any Trainer', async () => {
    renderAdminUsers({
      ...fixtures.superAdmin,
      id: IMPERSONATION.target.user_id,
      role: 'trainer',
      impersonation: IMPERSONATION,
    })

    expect(
      await screen.findByText("You don't have access to this page", {}, { timeout: 5000 }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('lets a real Super Admin through, not impersonating anyone', async () => {
    renderAdminUsers(fixtures.superAdmin)

    expect(await screen.findByRole('table', {}, { timeout: 5000 })).toBeInTheDocument()
  })
})
