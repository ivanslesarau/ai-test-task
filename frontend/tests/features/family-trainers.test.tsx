import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { AddTrainerForm } from '@/features/family/add-trainer/ui/add-trainer-form'
import { RemoveTrainerDialog } from '@/features/family/remove-trainer/ui/remove-trainer-dialog'

import { server } from '../msw-server'

function renderAddTrainerForm(onSuccess: () => void = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <AddTrainerForm profileId="profile-child" existingTrainerIds={[]} onSuccess={onSuccess} />
    </QueryClientProvider>,
  )
}

function renderRemoveTrainerDialog(onOpenChange: (open: boolean) => void = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <RemoveTrainerDialog
        open
        onOpenChange={onOpenChange}
        profileId="profile-child"
        associationId="assoc-1"
        playerDisplayName="Charlie Parent"
        trainerDisplayName="Coach Lisa"
      />
    </QueryClientProvider>,
  )
}

describe('AddTrainerForm — exactly one of code or trainer_id (FR-125)', () => {
  it('refuses submission when neither code nor trainer is supplied', async () => {
    server.use(http.get('/api/v1/me/contexts', () => HttpResponse.json({ active_player_profile_id: null, active_trainer_id: null, contexts: [] })))
    renderAddTrainerForm()

    await userEvent.click(await screen.findByRole('button', { name: /add trainer/i }))

    expect(
      await screen.findByText(/enter an invitation code, or choose a trainer/i),
    ).toBeInTheDocument()
  })

  it('refuses submission when both a code and a trainer are supplied', async () => {
    server.use(
      http.get('/api/v1/me/contexts', () =>
        HttpResponse.json({
          active_player_profile_id: null,
          active_trainer_id: null,
          contexts: [
            {
              player_profile_id: 'profile-self',
              player_display_name: 'Pat Parent',
              player_profile_kind: 'self',
              trainer_id: 'trainer-a',
              trainer_display_name: 'Coach Amy',
              branding: { logo_url: null, primary_color: null, updated_at: null },
              joined_at: '2026-01-01T00:00:00Z',
            },
          ],
        }),
      ),
    )
    renderAddTrainerForm()

    await userEvent.type(
      await screen.findByLabelText(/invitation code/i),
      'a-valid-code-1234',
    )
    // Selecting the trainer via the native select element underneath —
    // Radix's Select is exercised elsewhere; here the point is the
    // combined-refusal rule, so setting both form values is what matters.
    const combobox = screen.getByRole('combobox')
    await userEvent.click(combobox)
    const listbox = await screen.findByRole('listbox')
    await userEvent.click(within(listbox).getByText('Coach Amy'))

    await userEvent.click(screen.getByRole('button', { name: /add trainer/i }))

    expect(
      await screen.findByText(/enter an invitation code, or choose a trainer/i),
    ).toBeInTheDocument()
  })

  it('submits successfully with a code alone', async () => {
    server.use(
      http.get('/api/v1/me/contexts', () =>
        HttpResponse.json({ active_player_profile_id: null, active_trainer_id: null, contexts: [] }),
      ),
      http.post('/api/v1/me/players/profile-child/trainers', () =>
        HttpResponse.json({
          id: 'profile-child',
          kind: 'child',
          display_name: 'Charlie Parent',
          first_name: 'Charlie',
          last_name: 'Parent',
          date_of_birth: '2016-01-01',
          age: 10,
          gender: 'other',
          school: null,
          jersey_number: null,
          skill_level: null,
          photo_url: null,
          tokens_without_approval: false,
          has_sign_in: false,
          associations: [],
        }),
      ),
    )
    const onSuccess = vi.fn()
    renderAddTrainerForm(onSuccess)

    await userEvent.type(
      await screen.findByLabelText(/invitation code/i),
      'a-valid-code-1234',
    )
    await userEvent.click(screen.getByRole('button', { name: /add trainer/i }))

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1))
  })
})

describe('RemoveTrainerDialog — confirmation before removal (FR-126)', () => {
  it('states the reservation consequence before confirming', async () => {
    renderRemoveTrainerDialog()

    expect(await screen.findByText(/charlie parent will no longer train with coach lisa/i)).toBeInTheDocument()
    expect(screen.getByText(/upcoming reservations with this trainer will be cancelled/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /remove trainer/i })).toBeInTheDocument()
  })

  it('removes the trainer on confirmation', async () => {
    server.use(
      http.delete('/api/v1/me/players/profile-child/trainers/assoc-1', () => new HttpResponse(null, { status: 204 })),
    )
    const onOpenChange = vi.fn()
    renderRemoveTrainerDialog(onOpenChange)

    await userEvent.click(await screen.findByRole('button', { name: /remove trainer/i }))

    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false))
  })
})
