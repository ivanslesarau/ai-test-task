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

function mockTrainerSession() {
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
    http.get('/api/v1/me/share-link', () =>
      HttpResponse.json({
        id: 'link-1',
        code: 'abc123',
        url: 'https://example.org/join/abc123',
        kind: 'player_standing',
        is_active: true,
        use_count: 0,
        expires_at: null,
        max_uses: null,
        created_at: '2026-01-01T00:00:00Z',
      }),
    ),
    http.get('/api/v1/me/branding', () =>
      HttpResponse.json({ logo_url: null, primary_color: null, updated_at: null }),
    ),
  )
}

function mockCoachSession() {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-coach-1',
        email: 'coach@example.org',
        role: 'coach',
        status: 'active',
        first_name: 'Cody',
        last_name: 'Coach',
        photo_url: null,
      }),
    ),
  )
}

function mockPlayerParentSession() {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-player-1',
        email: 'player@example.org',
        role: 'player_parent',
        status: 'active',
        first_name: 'Pat',
        last_name: 'Player',
        photo_url: null,
        active_player_profile_id: null,
        active_trainer_id: null,
        context_count: 0,
        is_child_account: false,
      }),
    ),
    // TrainerContextSwitcher reads this unconditionally (it decides
    // switcher vs. label vs. nothing only after the query resolves).
    http.get('/api/v1/me/contexts', () =>
      HttpResponse.json({ active_player_profile_id: null, active_trainer_id: null, contexts: [] }),
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

  it('lists Users in the primary nav for a Super Admin', async () => {
    mockSuperAdminSession()
    renderAt('/')

    await screen.findByText('Ada Admin')
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    expect(within(nav).getByRole('link', { name: 'Users' })).toBeInTheDocument()
  })

  it('lists Portal settings and Players in the primary nav for a Trainer', async () => {
    mockTrainerSession()
    renderAt('/')

    await screen.findByText('Tara Trainer')
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    expect(within(nav).getByRole('link', { name: 'Portal settings' })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'Players' })).toBeInTheDocument()
  })

  it('renders no primary nav for a Coach', async () => {
    mockCoachSession()
    renderAt('/')

    await screen.findByText('Cody Coach')
    expect(screen.queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument()
  })

  it('lists Family in the primary nav for a Player/Parent', async () => {
    // Extension (2026-08-27, family accounts, tasks.md T365): supersedes
    // "renders no primary nav for a Player/Parent" — D-07's empty list
    // was correct only until this feature gave the role a page.
    mockPlayerParentSession()
    renderAt('/')

    await screen.findByText('Pat Player')
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    expect(within(nav).getByRole('link', { name: 'Family' })).toBeInTheDocument()
  })

  it('marks the active section on the primary nav', async () => {
    mockTrainerSession()
    renderAt('/trainer/portal')

    await screen.findByRole('heading', { name: 'Portal settings' })
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    const portalLink = within(nav).getByRole('link', { name: 'Portal settings' })
    const playersLink = within(nav).getByRole('link', { name: 'Players' })
    // TanStack Router marks the active `<Link>` with `data-status="active"` —
    // a stable signal that doesn't collide with the `hover:bg-accent`
    // Tailwind class every ghost-variant Button already carries.
    expect(portalLink).toHaveAttribute('data-status', 'active')
    expect(playersLink).not.toHaveAttribute('data-status', 'active')
  })

  it('renders Home > Portal settings on /trainer/portal', async () => {
    mockTrainerSession()
    renderAt('/trainer/portal')

    await screen.findByRole('heading', { name: 'Portal settings' })
    const breadcrumb = screen.getByRole('navigation', { name: /breadcrumb/i })
    expect(breadcrumb).toHaveTextContent('Home')
    expect(breadcrumb).toHaveTextContent('Portal settings')

    const homeLink = within(breadcrumb).getByRole('link', { name: 'Home' })
    expect(homeLink).toHaveAttribute('href', '/')

    const currentCrumb = within(breadcrumb).getByText('Portal settings')
    expect(currentCrumb).toHaveAttribute('aria-current', 'page')
  })
})
