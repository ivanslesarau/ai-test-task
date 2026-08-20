import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { EditProfileForm } from '@/features/profile/edit-own/ui/edit-profile-form'
import type { OwnProfile } from '@/shared/api/types'

import { server } from '../msw-server'

function renderForm(profile: OwnProfile) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <EditProfileForm profile={profile} />
    </QueryClientProvider>,
  )
}

const coachProfile: OwnProfile = {
  id: 'user-coach-1',
  email: 'coach@example.org',
  role: 'coach',
  status: 'active',
  created_at: '2026-01-01T00:00:00Z',
  first_name: 'Cody',
  last_name: 'Coach',
  phone: null,
  photo_url: null,
  thumbnail_url: null,
  role_detail: {
    bio: null,
    credentials: null,
    certifications: null,
    is_publicly_visible: false,
  },
  editable_fields: ['first_name', 'last_name', 'phone', 'bio', 'is_publicly_visible'],
}

describe('EditProfileForm', () => {
  it('renders only the fields the server marked editable', () => {
    renderForm(coachProfile)

    expect(screen.getByLabelText('First name')).toBeInTheDocument()
    expect(screen.getByLabelText('Bio')).toBeInTheDocument()
    expect(screen.getByLabelText('Publicly visible profile')).toBeInTheDocument()

    // Read-only/identity fields, and fields not in editable_fields for
    // this role (jersey_number belongs to player_parent), never render
    // as inputs at all.
    expect(screen.queryByLabelText(/^email$/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/jersey number/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/business name/i)).not.toBeInTheDocument()
  })

  it('submits only the editable fields, never the read-only ones', async () => {
    let capturedBody: unknown = null
    server.use(
      http.patch('/api/v1/me/profile', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({ ...coachProfile, first_name: 'Changed' })
      }),
    )
    renderForm(coachProfile)

    await userEvent.clear(screen.getByLabelText('First name'))
    await userEvent.type(screen.getByLabelText('First name'), 'Changed')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(capturedBody).not.toBeNull())
    const body = capturedBody as Record<string, unknown>
    expect(body.first_name).toBe('Changed')
    expect(body).not.toHaveProperty('email')
    expect(body).not.toHaveProperty('role')
    expect(body).not.toHaveProperty('skill_level')
    expect(body).not.toHaveProperty('jersey_number')
  })
})
