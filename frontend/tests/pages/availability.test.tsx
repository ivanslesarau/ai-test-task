import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { AvailabilityWeek } from '@/shared/api/types'

import { server } from '../msw-server'

const DEFAULT_BRANDING = { logo_url: null, primary_color: null, updated_at: null }

const GRACE_ENTRY = {
  player_profile_id: 'profile-grace',
  player_display_name: 'Grace Family',
  player_profile_kind: 'child',
  trainer_id: 'trainer-a',
  trainer_display_name: 'Trainer A',
  branding: DEFAULT_BRANDING,
  joined_at: '2026-01-01T00:00:00Z',
}

const LEO_ENTRY = {
  player_profile_id: 'profile-leo',
  player_display_name: 'Leo Family',
  player_profile_kind: 'child',
  trainer_id: 'trainer-b',
  trainer_display_name: 'Trainer B',
  branding: DEFAULT_BRANDING,
  joined_at: '2026-01-02T00:00:00Z',
}

function mockFamilySession(overrides: Record<string, unknown> = {}) {
  const session = {
    id: 'parent-1',
    email: 'parent@example.org',
    role: 'player_parent' as const,
    status: 'active' as const,
    first_name: 'Pat',
    last_name: 'Parent',
    photo_url: null,
    active_player_profile_id: 'profile-grace',
    active_trainer_id: 'trainer-a',
    context_count: 2,
    is_child_account: false,
    portal_branding: DEFAULT_BRANDING,
    ...overrides,
  }

  server.use(
    http.get('/api/v1/auth/session', () => HttpResponse.json(session)),
    http.get('/api/v1/me/contexts', () =>
      HttpResponse.json({
        active_player_profile_id: session.active_player_profile_id,
        active_trainer_id: session.active_trainer_id,
        contexts: [GRACE_ENTRY, LEO_ENTRY],
      }),
    ),
    http.put('/api/v1/me/context', async ({ request }) => {
      const body = (await request.json()) as { player_profile_id: string; trainer_id: string }
      session.active_player_profile_id = body.player_profile_id
      session.active_trainer_id = body.trainer_id
      return HttpResponse.json({
        active_player_profile_id: body.player_profile_id,
        active_trainer_id: body.trainer_id,
        contexts: [GRACE_ENTRY, LEO_ENTRY],
      })
    }),
  )
  return session
}

function mockAvailabilityFor(profileId: string, week: AvailabilityWeek) {
  server.use(
    http.get(`/api/v1/me/players/${profileId}/availability`, () => HttpResponse.json(week)),
  )
}

function renderAvailabilityPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: ['/availability'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('AvailabilityPage', () => {
  it('names the selected profile unmistakably on screen', async () => {
    mockFamilySession()
    mockAvailabilityFor('profile-grace', { slots: [], updated_at: null })
    mockAvailabilityFor('profile-leo', { slots: [], updated_at: null })

    renderAvailabilityPage()

    await screen.findByTestId('availability-active-profile')
    await waitFor(() => {
      expect(screen.getByTestId('availability-active-profile')).toHaveTextContent('Grace Family')
    })
  })

  it('switching profiles switches the week that loads', async () => {
    mockFamilySession()
    mockAvailabilityFor('profile-grace', {
      slots: [{ day_of_week: 1, start_minute: 1020, end_minute: 1200 }],
      updated_at: '2026-08-01T00:00:00Z',
    })
    mockAvailabilityFor('profile-leo', {
      slots: [{ day_of_week: 5, start_minute: 540, end_minute: 720 }],
      updated_at: '2026-08-02T00:00:00Z',
    })

    renderAvailabilityPage()

    await screen.findByTestId('availability-active-profile')
    // Grace's Tuesday range is loaded into the editor.
    await waitFor(() => {
      expect(screen.getAllByText('No ranges stated.')).toHaveLength(6)
    })

    const trigger = await screen.findByLabelText(/switch trainer/i)
    await userEvent.click(trigger)
    const listbox = await screen.findByRole('listbox')
    await userEvent.click(within(listbox).getByText(/Leo Family/))

    await waitFor(
      () => {
        expect(screen.getByTestId('availability-active-profile')).toHaveTextContent(
          'Leo Family',
        )
      },
      { timeout: 10000 },
    )
    await waitFor(
      () => {
        expect(screen.getAllByText('No ranges stated.')).toHaveLength(6)
      },
      { timeout: 10000 },
    )
  }, 15000)

  it('a child sees only their own profile, with no switcher to another', async () => {
    mockFamilySession({
      id: 'child-1',
      is_child_account: true,
      context_count: 1,
      active_player_profile_id: 'profile-grace',
      active_trainer_id: 'trainer-a',
    })
    server.use(
      http.get('/api/v1/me/contexts', () =>
        HttpResponse.json({
          active_player_profile_id: 'profile-grace',
          active_trainer_id: 'trainer-a',
          contexts: [GRACE_ENTRY],
        }),
      ),
    )
    mockAvailabilityFor('profile-grace', { slots: [], updated_at: null })

    renderAvailabilityPage()

    expect(await screen.findByText(/Grace Family/)).toBeInTheDocument()
    expect(screen.queryByLabelText(/switch trainer/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Leo Family/)).not.toBeInTheDocument()
  })
})
