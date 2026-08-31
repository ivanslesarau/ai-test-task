import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { CoachInvitationList } from '@/features/trainer/coach-invitations/ui/coach-invitation-list'
import type { CoachInvitation, CoachInvitationPage } from '@/shared/api/types'

import { server } from '../../msw-server'

function invitation(overrides: Partial<CoachInvitation>): CoachInvitation {
  return {
    id: 'invitation',
    invited_email: 'someone@example.org',
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

function renderList() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <CoachInvitationList />
    </QueryClientProvider>,
  )
}

describe('CoachInvitationList', () => {
  it('shows one row per state with the actions each state permits', async () => {
    const page: CoachInvitationPage = {
      items: [
        invitation({ id: 'i-awaiting', invited_email: 'awaiting@example.org', state: 'awaiting' }),
        invitation({ id: 'i-accepted', invited_email: 'accepted@example.org', state: 'accepted' }),
        invitation({ id: 'i-expired', invited_email: 'expired@example.org', state: 'expired' }),
        invitation({ id: 'i-revoked', invited_email: 'revoked@example.org', state: 'revoked' }),
        invitation({
          id: 'i-blocked',
          invited_email: 'blocked@example.org',
          state: 'blocked',
          blocked_reason: 'already_assigned',
        }),
      ],
      total: 5,
      page: 1,
      page_size: 25,
    }
    server.use(http.get('/api/v1/trainer/coach-invitations', () => HttpResponse.json(page)))

    renderList()

    const rows = await screen.findAllByRole('listitem')
    expect(rows).toHaveLength(5)

    function rowFor(email: string): HTMLElement {
      const row = rows.find((candidate) => within(candidate).queryByText(email))
      if (!row) throw new Error(`no row found for ${email}`)
      return row
    }

    // awaiting: both actions
    expect(within(rowFor('awaiting@example.org')).getByRole('button', { name: 'Resend' })).toBeInTheDocument()
    expect(within(rowFor('awaiting@example.org')).getByRole('button', { name: 'Revoke' })).toBeInTheDocument()

    // accepted: neither action
    expect(within(rowFor('accepted@example.org')).queryByRole('button', { name: 'Resend' })).not.toBeInTheDocument()
    expect(within(rowFor('accepted@example.org')).queryByRole('button', { name: 'Revoke' })).not.toBeInTheDocument()

    // expired: resend only
    expect(within(rowFor('expired@example.org')).getByRole('button', { name: 'Resend' })).toBeInTheDocument()
    expect(within(rowFor('expired@example.org')).queryByRole('button', { name: 'Revoke' })).not.toBeInTheDocument()

    // revoked: neither action
    expect(within(rowFor('revoked@example.org')).queryByRole('button', { name: 'Resend' })).not.toBeInTheDocument()
    expect(within(rowFor('revoked@example.org')).queryByRole('button', { name: 'Revoke' })).not.toBeInTheDocument()

    // blocked: both actions
    expect(within(rowFor('blocked@example.org')).getByRole('button', { name: 'Resend' })).toBeInTheDocument()
    expect(within(rowFor('blocked@example.org')).getByRole('button', { name: 'Revoke' })).toBeInTheDocument()
  })

  it('renders no superseded rows because the server already excludes them', async () => {
    // The server never returns a superseded row (FR-005) — this list has
    // nothing to filter. This test documents that invariant rather than
    // exercising a filter that does not exist on the client.
    const page: CoachInvitationPage = {
      items: [invitation({ id: 'i-1', state: 'awaiting' })],
      total: 1,
      page: 1,
      page_size: 25,
    }
    server.use(http.get('/api/v1/trainer/coach-invitations', () => HttpResponse.json(page)))

    renderList()

    const rows = await screen.findAllByRole('listitem')
    expect(rows).toHaveLength(1)
  })

  it('shows an empty message when there are no invitations', async () => {
    server.use(
      http.get('/api/v1/trainer/coach-invitations', () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 25 }),
      ),
    )

    renderList()

    expect(await screen.findByText('No invitations yet.')).toBeInTheDocument()
  })
})
