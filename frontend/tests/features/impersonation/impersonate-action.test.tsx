import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'

import { useUiStore } from '@/app/store/ui-store'
import { routeTree } from '@/routeTree.gen'
import type { UserPage, UserSummary } from '@/shared/api/types'

import { fixtures } from '../../msw-handlers'
import { server } from '../../msw-server'

// The Zustand store is a module-level singleton, not reset between tests
// within a file — a dialog left open by one test would otherwise still be
// open (and `aria-hidden`-wrapping the rest of the tree) for the next.
afterEach(() => {
  useUiStore.getState().clearPendingAction()
})

function renderDirectory() {
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

function directoryPage(items: UserSummary[]): UserPage {
  return { items, page: 1, page_size: 25, total: items.length }
}

describe('the Impersonate row action', () => {
  it('does not appear on a Super Admin row', async () => {
    const superAdminRow: UserSummary = {
      ...fixtures.userDetail,
      id: 'user-super-admin-2',
      role: 'super_admin',
      first_name: 'Second',
      last_name: 'Admin',
    }
    server.use(
      http.get('/api/v1/admin/users', () => HttpResponse.json(directoryPage([superAdminRow]))),
    )

    renderDirectory()

    await screen.findByRole('table', {}, { timeout: 5000 })
    expect(screen.queryByRole('button', { name: /impersonate/i })).not.toBeInTheDocument()
  })

  it('does not appear on the caller\'s own row', async () => {
    const ownRow: UserSummary = {
      ...fixtures.userDetail,
      id: fixtures.superAdmin.id,
      role: 'super_admin',
    }
    server.use(http.get('/api/v1/admin/users', () => HttpResponse.json(directoryPage([ownRow]))))

    renderDirectory()

    await screen.findByRole('table', {}, { timeout: 5000 })
    expect(screen.queryByRole('button', { name: /impersonate/i })).not.toBeInTheDocument()
  })

  it('appears for an ordinary role and opens a confirmation naming the person and role', async () => {
    server.use(
      http.get('/api/v1/admin/users', () => HttpResponse.json(directoryPage([fixtures.userDetail]))),
    )

    renderDirectory()

    await screen.findByRole('table', {}, { timeout: 5000 })
    const button = screen.getByRole('button', { name: /impersonate/i })
    expect(button).toBeInTheDocument()

    await userEvent.click(button)

    const dialog = await screen.findByRole('alertdialog')
    expect(dialog).toHaveTextContent(fixtures.userDetail.first_name)
    expect(dialog).toHaveTextContent(fixtures.userDetail.last_name)
    expect(dialog).toHaveTextContent('Trainer')
  })

  it('does not appear on an already-erased row', async () => {
    const erasedRow: UserSummary = { ...fixtures.userDetail, status: 'deleted' }
    server.use(
      http.get('/api/v1/admin/users', () => HttpResponse.json(directoryPage([erasedRow]))),
    )

    renderDirectory()

    await screen.findByRole('table', {}, { timeout: 5000 })
    expect(screen.queryByRole('button', { name: /impersonate/i })).not.toBeInTheDocument()
  })
})
