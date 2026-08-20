# Frontend Contracts: Routes, Query Keys, and State Ownership

**Feature**: `001-user-roles-admin` | **Companion to**: [openapi.yaml](./openapi.yaml)

The backend contract says what the server accepts and returns. This document fixes the frontend's own
interfaces — the ones that must be agreed before implementation because more than one slice depends on
them: the route table, the TanStack Query key factory, the Zod schemas, and the boundary between
server state and client state.

Derived from constitution Principle IV and [research.md](./research.md) R-17, R-19.

---

## 1. Route table (TanStack Router, file-based)

Routes are generated from the file tree. Search parameters are validated with Zod at the route
definition, so every read of them is typed and no route builds a URL from a string.

| Route file | Path | Guard | Search params |
|---|---|---|---|
| `routes/__root.tsx` | — | Loads the current session once; provides it to the tree | — |
| `routes/login.tsx` | `/login` | Redirects to the role landing route if already signed in | `redirect?: string` |
| `routes/set-password.tsx` | `/set-password` | Public | `token: string` (required) |
| `routes/_authed.tsx` | — | Layout route: redirects to `/login` when there is no session | — |
| `routes/_authed/profile.tsx` | `/profile` | Any signed-in role | — |
| `routes/_authed/index.tsx` | `/` | Any signed-in role; renders per-role content | — |
| `routes/_authed/admin.tsx` | — | Layout route: 403 view unless role is `super_admin` | — |
| `routes/_authed/admin/users.index.tsx` | `/admin/users` | Super Admin | `page`, `page_size`, `q`, `role`, `status`, `sort` |
| `routes/_authed/admin/users.$userId.tsx` | `/admin/users/$userId` | Super Admin | — |

**Directory search-param schema** — the single source of truth for the directory's URL state:

```ts
// entities/user/model/directory-search.ts
export const directorySearchSchema = z.object({
  page: z.number().int().min(1).catch(1),
  page_size: z.number().int().min(1).max(100).catch(25),
  q: z.string().max(200).optional(),
  role: z.enum(['super_admin', 'trainer', 'coach', 'player_parent']).optional(),
  status: z.enum(['active', 'inactive', 'deleted']).optional(),
  sort: z.enum(['created_at_desc', 'created_at_asc', 'name_asc', 'name_desc']).catch('created_at_desc'),
})
export type DirectorySearch = z.infer<typeof directorySearchSchema>
```

`.catch(...)` rather than `.default(...)` on the numeric and enum fields so that a hand-edited or
stale URL degrades to a valid view instead of throwing — paging state is not worth an error boundary.

**On route guards**: these guards decide what to *render*. They are not security. Every rule they
express is enforced again by the server on each request (FR-015), and the `_admin` guard exists so a
Trainer who types `/admin/users` sees a clear refusal rather than an empty table full of failed
requests.

---

## 2. TanStack Query key factory

One factory, in `entities/user`, imported by every slice that reads or writes account data. Defined
in one place so a mutation can invalidate every affected view without each feature guessing at key
shapes.

```ts
// entities/user/api/query-keys.ts
export const userKeys = {
  all: ['users'] as const,
  session: ['session'] as const,
  ownProfile: ['users', 'me', 'profile'] as const,
  directory: (search: DirectorySearch) => ['users', 'directory', search] as const,
  detail: (userId: string) => ['users', 'detail', userId] as const,
  audit: (userId: string, page: number) => ['users', 'audit', userId, page] as const,
  erasureRecord: (userId: string) => ['users', 'erasure', userId] as const,
} as const
```

**Invalidation contract** — which mutation invalidates what. Getting this wrong is the most likely
source of a stale directory after an administrative action, so it is specified rather than left to
each feature:

| Mutation | Invalidates |
|---|---|
| `signIn` | `session` — then the router redirects |
| `signOut` | Clears the entire cache; no invalidation needed |
| `setupPassword` | Nothing — no session exists yet |
| `updateOwnProfile` | `ownProfile`, `session` (the header shows the name and photo) |
| `uploadOwnPhoto` / `deleteOwnPhoto` | `ownProfile`, `session` |
| `createUser` | `all` — the new row can land on any page under any filter |
| `deactivateUser` / `reactivateUser` | `detail(userId)`, and `all` for the directory |
| `eraseUser` | `detail(userId)`, `all`, `erasureRecord(userId)` |
| `reinviteUser` | `detail(userId)` — `has_password` and available actions may change |

`createUser` invalidates the whole `users` subtree rather than a computed page key: the new account's
position depends on the active sort and filters, so no narrower invalidation is correct.

---

## 3. Zod schemas mirroring backend validation

Each form's schema lives with its feature slice and mirrors the Pydantic constraint on the other side
of the boundary (constitution Principle II, boundary parity). The table is the checklist for keeping
the two in step; a change on either side without the other is a defect.

| Schema | Slice | Mirrors | Rules |
|---|---|---|---|
| `signInSchema` | `features/auth/sign-in` | `LoginRequest` | email format; password non-empty |
| `setPasswordSchema` | `features/auth/set-password` | `setupPassword` body | ≥12 and ≤128 characters; confirmation must match |
| `createUserSchema` | `features/admin/create-user` | `CreateUserRequest` | email format ≤320; names 1–100; phone parseable; `business_name` required only when role is `trainer` |
| `ownProfileSchema` | `features/profile/edit-own` | `OwnProfileUpdate` | discriminated by role, so a Coach's form cannot submit `jersey_number` |
| `eraseUserSchema` | `features/admin/erase-user` | `EraseUserRequest` | `reason` non-empty after trimming, ≤1000 |
| `directorySearchSchema` | `entities/user` | directory query parameters | as §1 |

Two constraints deliberately live **only** on the server and are surfaced as field errors from a 422
rather than duplicated in Zod:

- **Email uniqueness** — cannot be known client-side without a lookup, and a pre-check would race.
- **Breached-password membership** — the list is a server-side asset; shipping it to the browser
  would be a large download that reveals the check's contents.

The forms therefore map a 422 `fields` array onto their own field errors. That mapping is shared, in
`shared/api`, because every form needs it.

---

## 4. State ownership

The constitution's rule — TanStack Query owns all server state, Zustand only global client UI state —
resolves for this feature as follows.

**Owned by TanStack Query** (never copied into a store): the current session and account, the own
profile, the directory page, account detail, audit pages, erasure records.

**Owned by Zustand** — one small store, and nothing in it comes from an API response:

```ts
// app/store/ui-store.ts
interface UiState {
  isSidebarCollapsed: boolean
  theme: 'light' | 'dark' | 'system'
  // Which confirmation dialog is open, and for which account. The id is a routing
  // coordinate the UI already holds, not fetched data — the dialog reads the account
  // itself from the query cache.
  pendingAction: { kind: 'deactivate' | 'reactivate' | 'erase'; userId: string } | null
}
```

`pendingAction` holds a `userId` rather than an account object precisely so that no server data lands
in the store. The dialog resolves the account through `userKeys.detail(userId)`, meaning it renders
current data even if the directory refreshed underneath it.

**Owned by the URL** (via typed search params): the directory's page, search term, role filter, status
filter, and sort. This state is in the URL rather than a store so a Super Admin can share or bookmark a
filtered view, and so the back button behaves.

---

## 5. The axios layer

One instance in `shared/api`, and no component imports axios (constitution Principle IV).

```
shared/api/
├── client.ts          # the single axios instance: baseURL '/api/v1', withCredentials: true
├── interceptors.ts    # response interceptor → normalized error
├── errors.ts          # ApiError class, isApiError guard, field-error extraction
└── types.ts           # generated/maintained types matching openapi.yaml schemas
```

**Response interceptor contract**: every non-2xx response becomes a rejected `ApiError` carrying the
status, the `error.code`, the safe message, and the `fields` array when present. Callers therefore
never inspect a raw axios error, and `unknown` is narrowed once, in `isApiError`, rather than at every
call site.

**Two interceptor behaviours worth agreeing now**, because they are cross-cutting:

- A **401** clears the session query and redirects to `/login` with the current path as `redirect`,
  except when the failing request *is* the session query — otherwise the app would loop on load.
- A **403** does not redirect. It surfaces to the caller, because a 403 in this feature means a
  legitimate session attempted something its role forbids, and hiding that behind a redirect makes it
  undiagnosable.

`withCredentials: true` is required: the session is a cookie (R-03), not an `Authorization` header.

---

## 6. What the frontend must not infer

Three values come from the server and must not be recomputed client-side, because doing so would let
the interface drift from what the server enforces:

| Value | Source | Why not computed locally |
|---|---|---|
| `editable_fields` | `GET /me/profile` | The read-only rule is FR-033's, enforced server-side. A local copy would silently diverge. |
| `available_actions` | `GET /admin/users/{id}` | Which of deactivate/reactivate/erase/reinvite is valid depends on status *and* `has_password`. One rule, one place. |
| `version` | `GET /admin/users/{id}` | Optimistic-concurrency token (R-10). Must be echoed exactly as received, never incremented locally. |
