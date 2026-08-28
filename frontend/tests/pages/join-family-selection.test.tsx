import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { JoinResult } from '@/shared/api/types'

import { server } from '../msw-server'

const DEFAULT_BRANDING = { logo_url: null, primary_color: null, updated_at: null }

function renderJoinPage(code: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [`/join/${code}`] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

function mockChooseFamilyMembersPreview(trainerName = 'Third Academy') {
  server.use(
    http.get('/api/v1/join/:code', () =>
      HttpResponse.json({
        trainer_display_name: trainerName,
        branding: DEFAULT_BRANDING,
        viewer: {
          state: 'choose_family_members',
          selectable_profiles: [
            {
              player_profile_id: 'profile-self',
              display_name: 'Pat Parent',
              kind: 'self',
              already_associated: false,
            },
            {
              player_profile_id: 'profile-alex',
              display_name: 'Alex Family',
              kind: 'child',
              already_associated: false,
            },
            {
              player_profile_id: 'profile-maya',
              display_name: 'Maya Family',
              kind: 'child',
              already_associated: true,
            },
          ],
        },
      }),
    ),
  )
}

describe('JoinPage — the family-member picker (US13, tasks.md T418)', () => {
  it('lists the account holder and every child, marking the already-connected one', async () => {
    mockChooseFamilyMembersPreview()
    renderJoinPage('abc123')

    expect(await screen.findByText('Pat Parent')).toBeInTheDocument()
    expect(screen.getByText('Alex Family')).toBeInTheDocument()
    expect(screen.getByText(/Maya Family/)).toBeInTheDocument()
    expect(screen.getByText(/already connected/i)).toBeInTheDocument()

    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes).toHaveLength(3)
    const mayaCheckbox = checkboxes[2]
    expect(mayaCheckbox).toBeDisabled()
    expect(mayaCheckbox).toBeChecked()
  })

  it('submits an empty selection without error', async () => {
    mockChooseFamilyMembersPreview()
    renderJoinPage('abc123')

    let capturedBody: unknown = 'not-called'
    server.use(
      http.post('/api/v1/join/:code/accept', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({
          trainer_id: 'trainer-1',
          trainer_display_name: 'Third Academy',
          associated_profile_ids: [],
          already_associated_profile_ids: [],
          active_player_profile_id: null,
          active_trainer_id: null,
        } satisfies JoinResult)
      }),
    )

    await screen.findByText('Pat Parent')
    await userEvent.click(screen.getByRole('button', { name: /join third academy/i }))

    expect(capturedBody).toEqual({ player_profile_ids: [] })
  })

  it('submits exactly the selected profiles', async () => {
    mockChooseFamilyMembersPreview()
    renderJoinPage('abc123')

    let capturedBody: unknown = 'not-called'
    server.use(
      http.post('/api/v1/join/:code/accept', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({
          trainer_id: 'trainer-1',
          trainer_display_name: 'Third Academy',
          associated_profile_ids: ['profile-self', 'profile-alex'],
          already_associated_profile_ids: [],
          active_player_profile_id: 'profile-self',
          active_trainer_id: 'trainer-1',
        } satisfies JoinResult)
      }),
    )

    await screen.findByText('Pat Parent')
    const checkboxes = screen.getAllByRole('checkbox')
    await userEvent.click(checkboxes[0])
    await userEvent.click(checkboxes[1])
    await userEvent.click(screen.getByRole('button', { name: /join third academy/i }))

    expect(capturedBody).toEqual({ player_profile_ids: ['profile-self', 'profile-alex'] })
  })
})
