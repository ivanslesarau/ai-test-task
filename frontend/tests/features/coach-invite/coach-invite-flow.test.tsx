import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { routeTree } from '@/routeTree.gen'
import type { CoachInvitationPreview, CoachRegistrationRequest, CurrentUser } from '@/shared/api/types'

import { server } from '../../msw-server'

const DEFAULT_BRANDING = { logo_url: null, primary_color: null, updated_at: null }

function preview(overrides: Partial<CoachInvitationPreview> = {}): CoachInvitationPreview {
  return {
    invited_email: 'nadia@example.org',
    invitee_name: null,
    message: null,
    expires_at: '2026-09-01T00:00:00Z',
    account_exists: false,
    trainer: { business_name: 'Rising Stars FC', portal_branding: DEFAULT_BRANDING },
    ...overrides,
  }
}

function mockPreview(data: CoachInvitationPreview | { error: { code: string; message: string } }, status = 200) {
  server.use(
    http.get('/api/v1/coach-invitations/:token', () => HttpResponse.json(data, { status })),
  )
}

function mockSignedOut() {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json(
        { error: { code: 'not_authenticated', message: 'Sign in to continue.' } },
        { status: 401 },
      ),
    ),
  )
}

function mockSignedInCoach(overrides: Partial<CurrentUser> = {}): CurrentUser {
  const session: CurrentUser = {
    id: 'user-coach-1',
    email: 'nadia@example.org',
    role: 'coach',
    status: 'active',
    first_name: 'Nadia',
    last_name: 'Newcoach',
    photo_url: null,
    active_player_profile_id: null,
    active_trainer_id: null,
    context_count: 0,
    is_child_account: false,
    portal_branding: DEFAULT_BRANDING,
    ...overrides,
  }
  server.use(http.get('/api/v1/auth/session', () => HttpResponse.json(session)))
  return session
}

function renderCoachInvitePage(token = 'raw-token-value') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [`/coach-invite/${token}`] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

describe('the public coach-invite flow', () => {
  it("renders the trainer's brand from the preview", async () => {
    mockSignedOut()
    mockPreview(preview())

    renderCoachInvitePage()

    expect(await screen.findByRole('heading', { name: /join rising stars fc/i })).toBeInTheDocument()
    expect(screen.getByText(/nadia@example\.org/)).toBeInTheDocument()
  })

  it('registration sends no email, role, or trainer field', async () => {
    mockSignedOut()
    mockPreview(preview({ account_exists: false }))
    let capturedBody: Record<string, unknown> | null = null
    server.use(
      http.post('/api/v1/coach-invitations/:token/register', async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>
        return HttpResponse.json(
          { outcome: 'joined', trainer_business_name: 'Rising Stars FC', joined_at: '2026-01-01T00:00:00Z' },
          { status: 201 },
        )
      }),
    )

    renderCoachInvitePage()
    const user = userEvent.setup()

    await screen.findByLabelText(/first name/i)
    await user.type(screen.getByLabelText(/first name/i), 'Nadia')
    await user.type(screen.getByLabelText(/last name/i), 'Newcoach')
    await user.type(screen.getByLabelText(/^password$/i), 'correct-horse-battery-987654')
    await user.click(screen.getByRole('button', { name: /create account and join/i }))

    await waitFor(() => expect(capturedBody).not.toBeNull())
    const body = capturedBody as unknown as CoachRegistrationRequest & Record<string, unknown>
    expect(body).not.toHaveProperty('email')
    expect(body).not.toHaveProperty('role')
    expect(body).not.toHaveProperty('trainer_id')
    expect(body.first_name).toBe('Nadia')
  })

  it('renders the account_exists sign-in offer instead of a registration form', async () => {
    mockSignedOut()
    mockPreview(preview({ account_exists: true }))

    renderCoachInvitePage()

    expect(await screen.findByText(/an account already exists/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/first name/i)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument()
  })

  it('renders each accept refusal with the server message and no other-trainer hint', async () => {
    mockSignedInCoach()
    mockPreview(preview())
    server.use(
      http.post('/api/v1/coach-invitations/:token/accept', () =>
        HttpResponse.json(
          {
            error: {
              code: 'coach_already_assigned',
              message: 'You already work with a trainer. Leave that trainer before accepting this invitation.',
            },
          },
          { status: 409 },
        ),
      ),
    )

    renderCoachInvitePage()
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /join rising stars fc/i }))

    const refusal = await screen.findByRole('alert')
    expect(refusal).toHaveTextContent(/already work with a trainer/i)
    // SC-003: no rendered text anywhere on the page names another trainer
    // — "Trainer B Sporting Club" is a distinct business name the page
    // never received from the server, so it cannot leak into the DOM.
    expect(document.body.textContent).not.toContain('Trainer B Sporting Club')
    expect(document.body.textContent).not.toContain('Sporting Club')
  })

  it('a dead link renders the single refusal message, not a stack trace', async () => {
    mockSignedOut()
    mockPreview(
      { error: { code: 'invitation_link_invalid', message: 'This invitation is no longer valid.' } },
      404,
    )

    renderCoachInvitePage()

    expect(await screen.findByText(/this link is no longer valid/i)).toBeInTheDocument()
  })
})
