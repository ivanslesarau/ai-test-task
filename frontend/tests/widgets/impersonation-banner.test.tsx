import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { CurrentUser, Impersonation } from '@/shared/api/types'

import { fixtures } from '../msw-handlers'
import { server } from '../msw-server'

function renderAuthed() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: ['/'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

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

function mockSession(overrides: Partial<CurrentUser>) {
  const session: CurrentUser = { ...fixtures.superAdmin, ...overrides }
  server.use(http.get('/api/v1/auth/session', () => HttpResponse.json(session)))
}

describe('ImpersonationBanner', () => {
  it('is absent when session.impersonation is null', async () => {
    mockSession({ impersonation: null })

    renderAuthed()

    await screen.findByRole('navigation', { name: 'Primary' }, { timeout: 5000 })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('is present, naming both parties, whenever session.impersonation is set', async () => {
    mockSession({
      id: IMPERSONATION.target.user_id,
      role: 'trainer',
      first_name: 'Tara',
      last_name: 'Trainer',
      impersonation: IMPERSONATION,
    })

    renderAuthed()

    const banner = await screen.findByRole('status', {}, { timeout: 5000 })
    expect(banner).toHaveTextContent('Tara Trainer')
    expect(banner).toHaveTextContent('Ada Admin')
    expect(screen.getByRole('button', { name: /exit/i })).toBeInTheDocument()
  })

  it('renders regardless of the effective role, never inferring from a role mismatch', async () => {
    // The effective session describes a Coach (the impersonated person);
    // presence is driven purely by `impersonation`, not by comparing
    // roles client-side (frontend-contracts.md §35, §38).
    mockSession({
      id: 'user-coach-1',
      role: 'coach',
      impersonation: { ...IMPERSONATION, target: { ...IMPERSONATION.target, role: 'coach' } },
    })

    renderAuthed()

    expect(await screen.findByRole('status', {}, { timeout: 5000 })).toBeInTheDocument()
  })
})
