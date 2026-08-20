import { http, HttpResponse } from 'msw'

import type {
  CreatedUser,
  CurrentUser,
  OwnProfile,
  UserDetail,
  UserPage,
} from '@/shared/api/types'

const BASE = '/api/v1'

/**
 * Shared fixtures, shaped exactly like the contracts in
 * specs/001-user-roles-admin/contracts/openapi.yaml, so a component test
 * exercising these handlers is exercising the real response shape.
 */
export const fixtures = {
  superAdmin: {
    id: 'user-super-admin-1',
    email: 'admin@example.org',
    role: 'super_admin',
    status: 'active',
    first_name: 'Ada',
    last_name: 'Admin',
    photo_url: null,
  } satisfies CurrentUser,

  trainerProfile: {
    id: 'user-trainer-1',
    email: 'trainer@example.org',
    role: 'trainer',
    status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    first_name: 'Tara',
    last_name: 'Trainer',
    phone: null,
    photo_url: null,
    thumbnail_url: null,
    role_detail: {
      business_name: 'Elite Basketball Academy',
      address: null,
      website: null,
      description: null,
    },
    editable_fields: ['first_name', 'last_name', 'phone', 'business_name', 'address', 'website', 'description'],
  } satisfies OwnProfile,

  userDetail: {
    id: 'user-trainer-1',
    email: 'trainer@example.org',
    first_name: 'Tara',
    last_name: 'Trainer',
    role: 'trainer',
    status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    thumbnail_url: null,
    has_password: true,
    version: 1,
    phone: null,
    photo_url: null,
    role_detail: {
      business_name: 'Elite Basketball Academy',
      address: null,
      website: null,
      description: null,
    },
    last_login_at: null,
    available_actions: ['deactivate', 'erase'],
  } satisfies UserDetail,
}

export const handlers = [
  http.get(`${BASE}/auth/session`, () => HttpResponse.json(fixtures.superAdmin)),

  http.post(`${BASE}/auth/login`, () => HttpResponse.json(fixtures.superAdmin)),

  http.post(`${BASE}/auth/logout`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${BASE}/me/profile`, () => HttpResponse.json(fixtures.trainerProfile)),

  http.get(`${BASE}/admin/users`, () =>
    HttpResponse.json({
      items: [fixtures.userDetail],
      page: 1,
      page_size: 25,
      total: 1,
    } satisfies UserPage),
  ),

  http.get(`${BASE}/admin/users/:userId`, () => HttpResponse.json(fixtures.userDetail)),

  http.post(`${BASE}/admin/users`, () =>
    HttpResponse.json(
      {
        user: fixtures.userDetail,
        invitation_sent: true,
        invitation_expires_at: '2026-01-02T00:00:00Z',
      } satisfies CreatedUser,
      { status: 201 },
    ),
  ),
]
