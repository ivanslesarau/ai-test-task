import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRouter,
} from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { ImpersonationHistoryTable } from '@/features/admin/impersonation/ui/impersonation-history-table'
import type { Impersonation, ImpersonationPage } from '@/shared/api/types'

import { server } from '../../msw-server'

function mockHistory(items: Impersonation[]) {
  const page: ImpersonationPage = { items, total: items.length, page: 1, page_size: 25 }
  server.use(http.get('/api/v1/admin/impersonations', () => HttpResponse.json(page)))
}

// A minimal one-route tree, rather than the app's full `routeTree` — this
// test exercises `ImpersonationHistoryTable` in isolation, and the only
// thing it needs from the router is a `useNavigate({ from:
// '/admin/impersonations' })` context (mirrors
// tests/features/coach-invitations/coach-roster-table.test.tsx).
function renderTable() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const rootRoute = createRootRoute({
    component: () => <ImpersonationHistoryTable search={{ page: 1, page_size: 25 }} />,
  })
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: ['/'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

const CLOSED_ROW: Impersonation = {
  id: 'imp-1',
  admin: { user_id: 'admin-1', display_name: 'Ada Admin', role: 'super_admin' },
  target: { user_id: 'trainer-1', display_name: 'Tara Trainer', role: 'trainer' },
  target_status_at_start: 'active',
  started_at: '2026-08-20T10:00:00Z',
  expires_at: '2026-08-20T11:00:00Z',
  ended_at: '2026-08-20T10:20:00Z',
  end_reason: 'exited',
  duration_seconds: 1200,
}

describe('ImpersonationHistoryTable', () => {
  it('shows an empty state when there is no history', async () => {
    mockHistory([])

    renderTable()

    expect(await screen.findByText('No impersonations recorded.')).toBeInTheDocument()
  })

  it('lists a closed row with both participants, duration, and end reason', async () => {
    mockHistory([CLOSED_ROW])

    renderTable()

    expect(await screen.findByText('Ada Admin')).toBeInTheDocument()
    expect(screen.getByText('Tara Trainer')).toBeInTheDocument()
    expect(screen.getByText('20m 0s')).toBeInTheDocument()
    expect(screen.getByText('exited')).toBeInTheDocument()
  })
})
