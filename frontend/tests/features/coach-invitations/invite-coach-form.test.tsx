import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { InviteCoachForm } from '@/features/trainer/coach-invitations/ui/invite-coach-form'
import type { CoachInvitation } from '@/shared/api/types'

import { server } from '../../msw-server'

function renderForm() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <InviteCoachForm />
    </QueryClientProvider>,
  )
}

function invitation(overrides: Partial<CoachInvitation> = {}): CoachInvitation {
  return {
    id: 'invitation-1',
    invited_email: 'prospect@example.org',
    invitee_name: null,
    message: null,
    state: 'awaiting',
    issued_at: '2026-01-01T00:00:00Z',
    expires_at: '2026-01-08T00:00:00Z',
    accepted_at: null,
    revoked_at: null,
    blocked_reason: null,
    coach: null,
    ...overrides,
  }
}

describe('InviteCoachForm', () => {
  it('does not validate on keystroke, only on submit', async () => {
    renderForm()

    await userEvent.type(screen.getByLabelText(/^email$/i), 'not-an-email')
    // No error yet — validation runs on submit, not on every keystroke.
    expect(screen.queryByText(/invalid email/i)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /invite coach/i }))

    expect(await screen.findByText(/invalid email/i)).toBeInTheDocument()
  })

  it('submits the happy path and normalizes empty optional fields to null', async () => {
    let capturedBody: unknown = null
    server.use(
      http.post('/api/v1/trainer/coach-invitations', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(invitation(), { status: 201 })
      }),
    )
    renderForm()

    await userEvent.type(screen.getByLabelText(/^email$/i), 'prospect@example.org')
    // Name and message are left blank — the controlled inputs hold "".
    await userEvent.click(screen.getByRole('button', { name: /invite coach/i }))

    await waitFor(() => expect(capturedBody).not.toBeNull())
    expect(capturedBody).toEqual({
      email: 'prospect@example.org',
      invitee_name: null,
      message: null,
    })
  })

  it('submits a real name and message unchanged', async () => {
    let capturedBody: unknown = null
    server.use(
      http.post('/api/v1/trainer/coach-invitations', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(invitation(), { status: 201 })
      }),
    )
    renderForm()

    await userEvent.type(screen.getByLabelText(/^email$/i), 'prospect@example.org')
    await userEvent.type(screen.getByLabelText(/name \(optional\)/i), 'Alex Prospect')
    await userEvent.type(screen.getByLabelText(/message \(optional\)/i), 'Welcome!')
    await userEvent.click(screen.getByRole('button', { name: /invite coach/i }))

    await waitFor(() => expect(capturedBody).not.toBeNull())
    expect(capturedBody).toEqual({
      email: 'prospect@example.org',
      invitee_name: 'Alex Prospect',
      message: 'Welcome!',
    })
  })

  it('renders a 409 as an offer to resend or revoke the existing invitation', async () => {
    const existing = invitation({ id: 'existing-1', invited_email: 'dup@example.org' })
    server.use(
      http.post('/api/v1/trainer/coach-invitations', () =>
        HttpResponse.json(
          {
            error: {
              code: 'coach_invitation_pending',
              message: 'An invitation to this address is already awaiting a response.',
              invitation: existing,
            },
          },
          { status: 409 },
        ),
      ),
    )
    renderForm()

    await userEvent.type(screen.getByLabelText(/^email$/i), 'dup@example.org')
    await userEvent.click(screen.getByRole('button', { name: /invite coach/i }))

    expect(
      await screen.findByText(/already has an invitation from you/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^resend$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^revoke$/i })).toBeInTheDocument()
  })

  it('resends the existing invitation from the conflict dialog', async () => {
    const existing = invitation({ id: 'existing-1', invited_email: 'dup@example.org' })
    const onResend = vi.fn()
    server.use(
      http.post('/api/v1/trainer/coach-invitations', () =>
        HttpResponse.json(
          {
            error: {
              code: 'coach_invitation_pending',
              message: 'An invitation to this address is already awaiting a response.',
              invitation: existing,
            },
          },
          { status: 409 },
        ),
      ),
      http.post('/api/v1/trainer/coach-invitations/existing-1/resend', () => {
        onResend()
        return HttpResponse.json(invitation({ id: 'existing-2' }), { status: 201 })
      }),
    )
    renderForm()

    await userEvent.type(screen.getByLabelText(/^email$/i), 'dup@example.org')
    await userEvent.click(screen.getByRole('button', { name: /invite coach/i }))
    await userEvent.click(await screen.findByRole('button', { name: /^resend$/i }))

    await waitFor(() => expect(onResend).toHaveBeenCalledTimes(1))
  })
})
