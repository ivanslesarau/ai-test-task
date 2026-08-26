import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen, within } from '@testing-library/react'
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

describe('AppShell', () => {
  it('renders no shell chrome on the public /login route', async () => {
    renderAt('/login')

    await screen.findByRole('heading', { name: /sign in/i })
    expect(screen.queryByRole('button', { name: /sign out/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: /breadcrumb/i })).not.toBeInTheDocument()
  })

  it('renders no shell chrome on the public /set-password route', async () => {
    server.use(
      http.get('/api/v1/auth/setup-password/:token', () =>
        HttpResponse.json({ email_hint: 'a***@example.org' }),
      ),
    )
    renderAt('/set-password?token=abc')

    await screen.findByRole('heading', { name: /set your password/i })
    expect(screen.queryByRole('button', { name: /sign out/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: /breadcrumb/i })).not.toBeInTheDocument()
  })

  it('renders the shell, with a breadcrumb matching the route, on the dashboard', async () => {
    mockSuperAdminSession()
    renderAt('/')

    expect(await screen.findByRole('button', { name: /sign out/i })).toBeInTheDocument()
    const breadcrumb = screen.getByRole('navigation', { name: /breadcrumb/i })
    expect(breadcrumb).toHaveTextContent('Home')
  })

  it('renders the shell, with a breadcrumb matching the route, on the profile page', async () => {
    mockSuperAdminSession()
    renderAt('/profile')

    expect(await screen.findByRole('heading', { name: 'My profile' })).toBeInTheDocument()
    const breadcrumb = screen.getByRole('navigation', { name: /breadcrumb/i })
    expect(breadcrumb).toHaveTextContent('Home')
    expect(breadcrumb).toHaveTextContent('Profile')
  })

  it('renders Home > Users on the filtered directory, Users as the current crumb', async () => {
    mockSuperAdminSession()
    server.use(
      http.get('/api/v1/admin/users', () =>
        HttpResponse.json({ items: [fixtures.userDetail], page: 1, page_size: 25, total: 1 }),
      ),
    )
    renderAt('/admin/users?role=trainer')

    await screen.findByRole('heading', { name: 'Users' })
    const breadcrumb = screen.getByRole('navigation', { name: /breadcrumb/i })
    expect(breadcrumb).toHaveTextContent('Home')
    expect(breadcrumb).toHaveTextContent('Users')

    // The active page's own crumb is text, not a link (a breadcrumb never
    // links to the page already on screen) — but the "Home" crumb ahead of
    // it is a real, typed link, and it is that link — not the directory's
    // own current-page crumb — that would need to carry search params if
    // it ever pointed at a filtered view.
    const homeLink = within(breadcrumb).getByRole('link', { name: 'Home' })
    expect(homeLink.tagName).toBe('A')
    expect(homeLink).toHaveAttribute('href', '/')

    // shadcn's BreadcrumbPage sets `role="link"` for assistive tech even
    // though it renders no `href` — `aria-current="page"` and the absence
    // of a real anchor are what distinguish the current, non-navigable
    // crumb from an actual link.
    const usersCrumb = within(breadcrumb).getByText('Users')
    expect(usersCrumb).toHaveAttribute('aria-current', 'page')
    expect(usersCrumb.tagName).not.toBe('A')
  })

  it('is the only place sign-out is reachable — not duplicated on any page', async () => {
    mockSuperAdminSession()
    renderAt('/')

    await screen.findByText('Ada Admin')
    const signOutButtons = screen.getAllByRole('button', { name: /sign out/i })
    expect(signOutButtons).toHaveLength(1)
    expect(signOutButtons[0].closest('header')).not.toBeNull()
  })
})
