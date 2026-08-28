import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createMemoryHistory, createRouter } from '@tanstack/react-router'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'

import { AddChildForm } from '@/features/family/add-child/ui/add-child-form'
import { routeTree } from '@/routeTree.gen'
import type { PlayerProfile, PlayerProfileList, TrainingContextList } from '@/shared/api/types'

import { server } from '../msw-server'

function mockPlayerParentSession() {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-parent-1',
        email: 'parent@example.org',
        role: 'player_parent',
        status: 'active',
        first_name: 'Pat',
        last_name: 'Parent',
        photo_url: null,
        active_player_profile_id: null,
        active_trainer_id: null,
        context_count: 0,
        is_child_account: false,
        portal_branding: { logo_url: null, primary_color: null, updated_at: null },
      }),
    ),
  )
}

const SELF_PROFILE: PlayerProfile = {
  id: 'profile-self',
  kind: 'self',
  display_name: 'Pat Parent',
  first_name: null,
  last_name: null,
  date_of_birth: null,
  age: null,
  gender: null,
  school: null,
  jersey_number: null,
  skill_level: null,
  photo_url: null,
  tokens_without_approval: false,
  has_sign_in: false,
  associations: [],
}

const CHILD_PROFILE: PlayerProfile = {
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
}

function mockFamilyList(profiles: PlayerProfile[]) {
  server.use(
    http.get('/api/v1/me/players', () =>
      HttpResponse.json({ profiles } satisfies PlayerProfileList),
    ),
  )
}

function mockChildAccountSession() {
  server.use(
    http.get('/api/v1/auth/session', () =>
      HttpResponse.json({
        id: 'user-child-1',
        email: 'charlie@example.org',
        role: 'player_parent',
        status: 'active',
        first_name: 'Charlie',
        last_name: 'Parent',
        photo_url: null,
        active_player_profile_id: null,
        active_trainer_id: null,
        context_count: 0,
        is_child_account: true,
        portal_branding: { logo_url: null, primary_color: null, updated_at: null },
      }),
    ),
  )
}

function mockContexts(trainerCount: 0 | 1 | 2) {
  const entries = Array.from({ length: trainerCount }, (_, i) => ({
    player_profile_id: 'profile-self',
    player_display_name: 'Pat Parent',
    player_profile_kind: 'self' as const,
    trainer_id: `trainer-${i}`,
    trainer_display_name: `Trainer ${i}`,
    branding: { logo_url: null, primary_color: null, updated_at: null },
    joined_at: '2026-01-01T00:00:00Z',
  }))
  server.use(
    http.get('/api/v1/me/contexts', () =>
      HttpResponse.json({
        active_player_profile_id: null,
        active_trainer_id: null,
        contexts: entries,
      } satisfies TrainingContextList),
    ),
  )
}

function renderFamilyPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: ['/family'] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

function renderAddChildForm(onSuccess: (profile: PlayerProfile) => void = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <AddChildForm onSuccess={onSuccess} />
    </QueryClientProvider>,
  )
}

async function fillRequiredFields() {
  await userEvent.type(screen.getByLabelText(/first name/i), 'Riley')
  await userEvent.type(screen.getByLabelText(/last name/i), 'Jordan')
  await userEvent.type(screen.getByLabelText(/date of birth/i), '2016-01-01')
  await userEvent.click(screen.getByRole('combobox'))
  const listbox = await screen.findByRole('listbox')
  await userEvent.click(within(listbox).getByText('Other'))
}

describe('FamilyPage — the roster', () => {
  it('renders the account holder and children distinctly', async () => {
    mockPlayerParentSession()
    mockFamilyList([SELF_PROFILE, CHILD_PROFILE])
    mockContexts(0)

    renderFamilyPage()

    expect(await screen.findByText('Charlie Parent')).toBeInTheDocument()
    // "Pat Parent" also appears in the header (the signed-in person's
    // name) — the roster row is the second occurrence.
    expect(screen.getAllByText('Pat Parent').length).toBeGreaterThanOrEqual(2)
    // The account-holder marker distinguishes the self profile from the
    // child (FR-106) — only one "Me" badge, beside Pat's row.
    expect(screen.getAllByText('Me')).toHaveLength(1)
  })

  it('shows the empty state when the account holds no player profiles', async () => {
    mockPlayerParentSession()
    mockFamilyList([])
    mockContexts(0)

    renderFamilyPage()

    expect(await screen.findByText(/no players on this account yet/i)).toBeInTheDocument()
  })
})

describe('FamilyPage — a signed-in child (US11, T385, FR-131, FR-132)', () => {
  it('shows only its own profile and hides the parent-only "Add child" control', async () => {
    mockChildAccountSession()
    // The scoping is server-side (FR-132, R-48) — the fixture simply
    // reflects what `GET /me/players` returns for a child caller: their
    // own profile alone, never a sibling's.
    mockFamilyList([CHILD_PROFILE])
    mockContexts(0)

    renderFamilyPage()

    expect(await screen.findByText('Charlie Parent')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^add child$/i })).not.toBeInTheDocument()
  })
})

describe('AddChildForm — the trainer question in its three shapes (FR-122)', () => {
  it('asks nothing when the account trains with no one', async () => {
    mockContexts(0)
    renderAddChildForm()

    await screen.findByLabelText(/first name/i)
    expect(screen.queryByText(/connect this child with/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/which trainers/i)).not.toBeInTheDocument()
  })

  it('asks a single yes/no naming the one trainer', async () => {
    mockContexts(1)
    renderAddChildForm()

    expect(await screen.findByText(/also connect this child with trainer 0/i)).toBeInTheDocument()
    expect(screen.queryByText(/which trainers/i)).not.toBeInTheDocument()
  })

  it('offers a checklist when there are several trainers', async () => {
    mockContexts(2)
    renderAddChildForm()

    expect(await screen.findByText(/which trainers does this child train with/i)).toBeInTheDocument()
    expect(screen.getByText('Trainer 0')).toBeInTheDocument()
    expect(screen.getByText('Trainer 1')).toBeInTheDocument()
  })
})

describe('AddChildForm — the duplicate-confirmation dialog (FR-110, research.md R-45)', () => {
  it('appears on a 409 and resubmits with the acknowledgement', async () => {
    mockContexts(0)
    let acknowledged = false
    server.use(
      http.post('/api/v1/me/players', async ({ request }) => {
        const body = (await request.json()) as { acknowledge_possible_duplicate?: boolean }
        if (body.acknowledge_possible_duplicate) {
          acknowledged = true
          return HttpResponse.json({ ...CHILD_PROFILE, id: 'profile-child-2' }, { status: 201 })
        }
        return HttpResponse.json(
          {
            error: {
              code: 'possible_duplicate_profile',
              message: 'A player with this name and date of birth already exists.',
              matches: [CHILD_PROFILE],
            },
          },
          { status: 409 },
        )
      }),
    )
    const onSuccess = vi.fn()
    renderAddChildForm(onSuccess)

    await fillRequiredFields()

    await userEvent.click(screen.getByRole('button', { name: /add child/i }))

    expect(await screen.findByText(/a similar player already exists/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /add anyway/i }))

    await waitFor(() => expect(acknowledged).toBe(true))
    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1))
  })
})
