import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { TrainerContextSwitcher } from '@/widgets/trainer-context-switcher/ui/trainer-context-switcher'

import { server } from '../msw-server'

const DEFAULT_BRANDING = { logo_url: null, primary_color: null, updated_at: null }

function playerSession(overrides: Record<string, unknown> = {}) {
  return {
    id: 'player-1',
    email: 'player@example.org',
    role: 'player_parent',
    status: 'active',
    first_name: 'Pat',
    last_name: 'Player',
    photo_url: null,
    active_player_profile_id: 'profile-self',
    active_trainer_id: 'trainer-a',
    context_count: 2,
    is_child_account: false,
    portal_branding: DEFAULT_BRANDING,
    ...overrides,
  }
}

function mockSessionAndContexts(session: object, contexts: object[]) {
  const typedSession = session as {
    active_player_profile_id: string | null
    active_trainer_id: string | null
  }
  server.use(
    http.get('/api/v1/auth/session', () => HttpResponse.json(session)),
    http.get('/api/v1/me/contexts', () =>
      HttpResponse.json({
        active_player_profile_id: typedSession.active_player_profile_id,
        active_trainer_id: typedSession.active_trainer_id,
        contexts,
      }),
    ),
  )
}

function renderSwitcher() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <TrainerContextSwitcher />
    </QueryClientProvider>,
  )
}

const selfEntry = (trainerId: string, trainerName: string, joinedAt: string) => ({
  player_profile_id: 'profile-self',
  player_display_name: 'Pat Player',
  player_profile_kind: 'self',
  trainer_id: trainerId,
  trainer_display_name: trainerName,
  branding: DEFAULT_BRANDING,
  joined_at: joinedAt,
})

const childEntry = (
  profileId: string,
  childName: string,
  trainerId: string,
  trainerName: string,
  joinedAt: string,
) => ({
  player_profile_id: profileId,
  player_display_name: childName,
  player_profile_kind: 'child',
  trainer_id: trainerId,
  trainer_display_name: trainerName,
  branding: DEFAULT_BRANDING,
  joined_at: joinedAt,
})

describe('TrainerContextSwitcher', () => {
  it('is not rendered when the caller has one context', async () => {
    mockSessionAndContexts(playerSession({ context_count: 1 }), [
      selfEntry('trainer-a', 'Trainer A', '2026-01-01'),
    ])
    renderSwitcher()

    // Give the session query a tick to resolve before asserting absence.
    await waitFor(() => expect(true).toBe(true))
    expect(screen.queryByLabelText(/switch trainer/i)).not.toBeInTheDocument()
  })

  it('groups self and child entries under separate headings for a parent', async () => {
    mockSessionAndContexts(playerSession({ context_count: 3 }), [
      selfEntry('trainer-a', 'Trainer A', '2026-01-01'),
      childEntry('profile-child-1', 'Alex', 'trainer-b', 'Trainer B', '2026-01-02'),
      childEntry('profile-child-2', 'Maya', 'trainer-b', 'Trainer B', '2026-01-03'),
    ])
    renderSwitcher()

    const trigger = await screen.findByLabelText(/switch trainer/i)
    await userEvent.click(trigger)
    const listbox = await screen.findByRole('listbox')

    expect(within(listbox).getByText('Your Training')).toBeInTheDocument()
    expect(within(listbox).getByText(/Your Children.s Training/)).toBeInTheDocument()
    expect(within(listbox).getByText(/Pat Player \(Me\) → Trainer A/)).toBeInTheDocument()
    expect(within(listbox).getByText(/Alex → Trainer B/)).toBeInTheDocument()
    expect(within(listbox).getByText(/Maya → Trainer B/)).toBeInTheDocument()
  })

  it('renders no heading for an empty group — a non-training parent sees only children', async () => {
    mockSessionAndContexts(playerSession({ context_count: 2, active_player_profile_id: 'profile-child-1' }), [
      childEntry('profile-child-1', 'Alex', 'trainer-a', 'Trainer A', '2026-01-01'),
      childEntry('profile-child-1', 'Alex', 'trainer-b', 'Trainer B', '2026-01-02'),
    ])
    renderSwitcher()

    const trigger = await screen.findByLabelText(/switch trainer/i)
    await userEvent.click(trigger)
    const listbox = await screen.findByRole('listbox')

    expect(within(listbox).queryByText('Your Training')).not.toBeInTheDocument()
    expect(within(listbox).getByText(/Your Children.s Training/)).toBeInTheDocument()
  })

  it("renders a flat list with no group headings for a signed-in child", async () => {
    mockSessionAndContexts(
      playerSession({
        id: 'child-1',
        context_count: 2,
        active_player_profile_id: 'profile-child-1',
        is_child_account: true,
      }),
      [
        childEntry('profile-child-1', 'Alex', 'trainer-a', 'Trainer A', '2026-01-01'),
        childEntry('profile-child-1', 'Alex', 'trainer-b', 'Trainer B', '2026-01-02'),
      ],
    )
    renderSwitcher()

    const trigger = await screen.findByLabelText(/switch trainer/i)
    await userEvent.click(trigger)
    const listbox = await screen.findByRole('listbox')

    expect(within(listbox).queryByText('Your Training')).not.toBeInTheDocument()
    expect(within(listbox).queryByText(/Your Children.s Training/)).not.toBeInTheDocument()
    expect(within(listbox).getByText('Trainer A')).toBeInTheDocument()
    expect(within(listbox).getByText('Trainer B')).toBeInTheDocument()
  })

  it('calls the switch endpoint with the selected pair', async () => {
    let switchedTo: { player_profile_id: string; trainer_id: string } | null = null
    mockSessionAndContexts(playerSession({ context_count: 2 }), [
      selfEntry('trainer-a', 'Trainer A', '2026-01-01'),
      childEntry('profile-child-1', 'Alex', 'trainer-b', 'Trainer B', '2026-01-02'),
    ])
    server.use(
      http.put('/api/v1/me/context', async ({ request }) => {
        const body = (await request.json()) as { player_profile_id: string; trainer_id: string }
        switchedTo = body
        return HttpResponse.json({
          active_player_profile_id: body.player_profile_id,
          active_trainer_id: body.trainer_id,
          contexts: [
            selfEntry('trainer-a', 'Trainer A', '2026-01-01'),
            childEntry('profile-child-1', 'Alex', 'trainer-b', 'Trainer B', '2026-01-02'),
          ],
        })
      }),
    )
    renderSwitcher()

    const trigger = await screen.findByLabelText(/switch trainer/i)
    await userEvent.click(trigger)
    const listbox = await screen.findByRole('listbox')
    await userEvent.click(within(listbox).getByText(/Alex → Trainer B/))

    await waitFor(() =>
      expect(switchedTo).toEqual({ player_profile_id: 'profile-child-1', trainer_id: 'trainer-b' }),
    )
  })
})
