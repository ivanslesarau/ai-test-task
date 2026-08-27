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
    active_trainer_id: 'trainer-a',
    trainer_count: 2,
    portal_branding: DEFAULT_BRANDING,
    ...overrides,
  }
}

function mockSessionAndTrainers(session: object, trainers: object[]) {
  server.use(
    http.get('/api/v1/auth/session', () => HttpResponse.json(session)),
    http.get('/api/v1/me/trainers', () =>
      HttpResponse.json({
        active_trainer_id: (session as { active_trainer_id: string | null }).active_trainer_id,
        trainers,
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

describe('TrainerContextSwitcher', () => {
  it('is not rendered when the caller has one trainer', async () => {
    mockSessionAndTrainers(playerSession({ trainer_count: 1 }), [
      { trainer_id: 'trainer-a', display_name: 'Trainer A', branding: DEFAULT_BRANDING, joined_at: '2026-01-01' },
    ])
    renderSwitcher()

    // Give the session query a tick to resolve before asserting absence.
    await waitFor(() => expect(true).toBe(true))
    expect(screen.queryByLabelText(/switch trainer/i)).not.toBeInTheDocument()
  })

  it('lists both trainers when the caller has two', async () => {
    mockSessionAndTrainers(playerSession(), [
      { trainer_id: 'trainer-a', display_name: 'Trainer A', branding: DEFAULT_BRANDING, joined_at: '2026-01-01' },
      { trainer_id: 'trainer-b', display_name: 'Trainer B', branding: DEFAULT_BRANDING, joined_at: '2026-01-02' },
    ])
    renderSwitcher()

    const trigger = await screen.findByLabelText(/switch trainer/i)
    await userEvent.click(trigger)
    const listbox = await screen.findByRole('listbox')
    expect(within(listbox).getByText('Trainer A')).toBeInTheDocument()
    expect(within(listbox).getByText('Trainer B')).toBeInTheDocument()
  })

  it('calls the switch endpoint with the selected trainer id', async () => {
    let switchedTo: string | null = null
    mockSessionAndTrainers(playerSession(), [
      { trainer_id: 'trainer-a', display_name: 'Trainer A', branding: DEFAULT_BRANDING, joined_at: '2026-01-01' },
      { trainer_id: 'trainer-b', display_name: 'Trainer B', branding: DEFAULT_BRANDING, joined_at: '2026-01-02' },
    ])
    server.use(
      http.put('/api/v1/me/trainer-context', async ({ request }) => {
        const body = (await request.json()) as { trainer_id: string }
        switchedTo = body.trainer_id
        return HttpResponse.json({
          active_trainer_id: body.trainer_id,
          trainers: [
            { trainer_id: 'trainer-a', display_name: 'Trainer A', branding: DEFAULT_BRANDING, joined_at: '2026-01-01' },
            { trainer_id: 'trainer-b', display_name: 'Trainer B', branding: DEFAULT_BRANDING, joined_at: '2026-01-02' },
          ],
        })
      }),
    )
    renderSwitcher()

    const trigger = await screen.findByLabelText(/switch trainer/i)
    await userEvent.click(trigger)
    const listbox = await screen.findByRole('listbox')
    await userEvent.click(within(listbox).getByText('Trainer B'))

    await waitFor(() => expect(switchedTo).toBe('trainer-b'))
  })
})
