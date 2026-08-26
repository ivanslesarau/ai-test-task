import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { UserPage } from '@/shared/api/types'

import { fixtures } from '../msw-handlers'
import { server } from '../msw-server'

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
  return router
}

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

function directoryPage(): UserPage {
  return { items: [fixtures.userDetail], page: 1, page_size: 25, total: 1 }
}

describe('UserDirectoryTable search debounce', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('issues exactly one request carrying the full term after a settled search', async () => {
    mockSuperAdminSession()
    const requests: (string | null)[] = []
    server.use(
      http.get('/api/v1/admin/users', ({ request }) => {
        requests.push(new URL(request.url).searchParams.get('q'))
        return HttpResponse.json(directoryPage())
      }),
    )

    renderDirectory()
    await vi.waitFor(() => expect(screen.getByRole('table')).toBeInTheDocument())
    const baseline = requests.length
    expect(requests.every((q) => q === null)).toBe(true)

    const input = screen.getByLabelText('Search by name or email') as HTMLInputElement
    for (const char of 'trainer') {
      fireEvent.change(input, { target: { value: input.value + char } })
    }

    // Not yet settled: no additional request during the debounce window.
    await vi.advanceTimersByTimeAsync(400)
    expect(requests).toHaveLength(baseline)

    await vi.advanceTimersByTimeAsync(200)
    await vi.waitFor(() => expect(requests).toHaveLength(baseline + 1))
    expect(requests.at(-1)).toBe('trainer')
  })
})

describe('UserDirectoryTable filters', () => {
  it('applies a role filter immediately, without debouncing', async () => {
    mockSuperAdminSession()
    const roleParams: (string | null)[] = []
    server.use(
      http.get('/api/v1/admin/users', ({ request }) => {
        roleParams.push(new URL(request.url).searchParams.get('role'))
        return HttpResponse.json(directoryPage())
      }),
    )

    renderDirectory()
    await screen.findByRole('table')
    const baseline = roleParams.length

    await userEvent.click(screen.getByLabelText('Filter by role'))
    const listbox = await screen.findByRole('listbox')
    await userEvent.click(within(listbox).getByText('Trainer'))

    await waitFor(() => expect(roleParams.length).toBeGreaterThan(baseline))
    expect(roleParams.at(-1)).toBe('trainer')
  })
})
