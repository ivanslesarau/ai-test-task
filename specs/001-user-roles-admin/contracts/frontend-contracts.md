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

**Two obligations every form carries**, in addition to its own schema:

| Obligation | Helper | Rule |
|---|---|---|
| Payload normalization | `shared/lib/normalize-payload.ts` | Every submit handler passes its values through `normalizeEmptyToNull` before `axios` sees them. Empty and whitespace-only strings become `null`; nothing else changes. Exactly one such helper exists (constitution Principle VI) — a second one, or an inline ternary at a call site, is a defect. |
| Error surfacing | `shared/lib/form-errors.ts` | Field errors render through `fieldErrorText`, which normalizes both Standard-Schema issue objects and plain strings. Server 422 field errors are injected with `form.setErrorMap({ onServer: toServerErrorMap(error) })`. No form reads `ApiError.fields` directly. |

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
├── media.ts           # resolveMediaUrl(): API-relative media path → DOM-usable URL
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

And one value the frontend **must** derive rather than use as received:

| Value | Source | Why it must be resolved locally |
|---|---|---|
| `photo_url`, `thumbnail_url` | any account or profile response | They are API-relative paths. Requests made through the axios instance resolve them against `baseURL` automatically; a DOM `src` does not, and resolves against the document origin instead. Every such value passes through `resolveMediaUrl` before reaching an `<img>` — the server is not asked to embed the API mount prefix, because that would put an HTTP concern in the service layer (constitution Principle III). |

---

## 7. Form validation timing and navigation chrome

Three conventions that cut across every slice. Fixed here because a form or page that deviates is
not locally wrong — it is inconsistent with the rest of the application, which is harder to spot.

### 7.1 Validation timing

Every form uses `validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' })`
with its Zod schema registered under `validators: { onDynamic }`.

| Moment | Behaviour |
|---|---|
| While typing, before any submit | Nothing validates and no message appears (FR-057) |
| On submit | Every field validates; each failure renders beside its own field (FR-058) |
| After the first submit | Fields revalidate on change, so corrections clear their messages live |

The submit button's `disabled` expression is `isSubmitting` **only**. It must not include
`canSubmit`: a button disabled by errors the person cannot yet see is FR-057's failure mode.

### 7.2 Server errors on a form

A 422 carrying `fields` is mapped onto the form with
`form.setErrorMap({ onServer: toServerErrorMap(error) })` in the mutation's `onError`. TanStack Form
distributes the `fields` entries onto the matching fields' `onServer` error slot, so they render
through the same `fieldErrorText` path as schema errors and no form needs its own mapping.

A 422 with no `fields`, and every other failure status, renders as the form-level message. A 409
(duplicate email, stale version) is form-level by nature — it describes the request, not a field.

### 7.3 Navigation chrome

| Element | Location | Rule |
|---|---|---|
| App shell | `widgets/app-shell`, mounted in `routes/_authed.tsx` | Identity, breadcrumb trail, profile link, sign-out, and the back-control region. Mounted at `_authed` and **not** at `__root`, because `__root` also carries `/login` and `/set-password`, which must show no signed-in chrome (FR-062) |
| Breadcrumbs | `widgets/app-shell/model/use-breadcrumbs.ts` | Derived from the router's matched routes as typed link descriptors. No URL is built from a string (Principle IV). The `/admin/users` crumb carries the active search params, so the trail returns to the filtered view |
| Back control | `shared/ui/back-button.tsx` | `history.back()` when `useCanGoBack()` is true, otherwise a typed `fallbackTo` route, which is required rather than optional so a deep-linked page always offers a way out. History-based back is what satisfies FR-061's "restore the filtered view" without threading search params through links |
| Search-term navigation | `widgets/user-directory-table` | Debounced 500 ms and navigated with `replace: true`, so typing leaves one history entry. Paging and filter changes push a normal entry — they are steps worth reversing (FR-063, SC-013) |

---

# Extension: Join Flow, Trainer Context & Branding

**Date**: 2026-08-26 | **Covers**: spec User Stories 6–8 | **Decisions**:
[research.md](./research.md) R-24 – R-27, R-29

## 8. Routes added

| Route file | Path | Guard | Search params |
|---|---|---|---|
| `routes/join.$code.tsx` | `/join/$code` | **Public** — renders for a visitor with no session and for a signed-in one | — |
| `routes/_authed/trainer.tsx` | — | Layout route: 403 view unless role is `trainer` | — |
| `routes/_authed/trainer/portal.tsx` | `/trainer/portal` | Trainer | — |
| `routes/_authed/trainer/players.tsx` | `/trainer/players` | Trainer | `page`, `page_size`, `q` |

`join.$code.tsx` sits beside `login.tsx` at the top level rather than under `_authed`, because
`_authed` redirects to `/login` when there is no session — which is exactly the visitor this page
exists for. It is also the one public route that renders branding, so the branding provider (§12)
mounts inside it as well as inside `_authed`.

The page branches on `viewer.state` from `GET /join/{code}`, never on its own reading of the session:

| `viewer.state` | Renders |
|---|---|
| `anonymous` | The registration form |
| `can_join` | The trainer's name and one confirm button (FR-080) |
| `already_associated` | "You already train with this trainer" and a link into their context (FR-082) |
| `role_cannot_join` | The explanation that the link is for players and parents (FR-081) |

Deciding this server-side matters: the four states depend on the caller's role *and* their existing
associations, and a client that inferred them would have to fetch the association list before
rendering a public page.

**Trainer settings are one page, not two.** `/trainer/portal` carries both the invitation link
(copy, regenerate) and branding (logo, colour, reset). The epic calls it "My Portal Settings", and
splitting a link the trainer copies from the identity they set beside it would put two routes where
the trainer thinks of one screen.

`/trainer/players` reuses the directory's debounce-and-replace convention from §7.3 — 500 ms,
`replace: true` on the search term, normal history entries for paging.

## 9. Query keys added

```ts
// entities/user/api/query-keys.ts — extended
export const userKeys = {
  // ... existing keys unchanged ...
  trainers: ['users', 'me', 'trainers'] as const,        // the switcher's list
  shareLink: ['users', 'me', 'share-link'] as const,     // trainer's own link
  branding: ['users', 'me', 'branding'] as const,        // trainer's own branding
} as const

// entities/join/api/query-keys.ts
export const joinKeys = {
  preview: (code: string) => ['join', 'preview', code] as const,
} as const

// entities/trainer-context/api/query-keys.ts — THE context namespace
export const ctxKeys = {
  root: ['ctx'] as const,
  scope: (trainerId: string) => ['ctx', trainerId] as const,
  players: (trainerId: string, search: RosterSearch) =>
    ['ctx', trainerId, 'players', search] as const,
} as const
```

**The `['ctx', trainerId, …]` namespace is a standing convention, not a local detail** (R-26). Every
query for data belonging to one trainer goes under it — the roster today, and every calendar, token
balance, reservation, and content list Epics 02–08 add. A component asking under the new trainer's
namespace cannot be served the previous trainer's cached response, which is what makes User Story 7
scenario 4 structurally true instead of a thing to remember.

The trainer's *own* keys stay outside the namespace: a trainer is not in a switchable context, and
their branding follows their account rather than a context.

**Invalidation contract — extended:**

| Mutation | Invalidates |
|---|---|
| `registerThroughJoinLink` | Nothing — a session is created, and the router lands the person in their new context |
| `acceptJoinLink` | `session`, `trainers`, and `removeQueries(ctxKeys.root)` — the context changed |
| `switchTrainerContext` | `session`, then `removeQueries(ctxKeys.root)` before rendering (R-26) |
| `regenerateShareLink` | `shareLink` |
| `updateBranding` / `uploadLogo` / `deleteLogo` / `resetBranding` | `branding`, `session` — the header repaints from the session's `portal_branding` |

`switchTrainerContext` awaits the mutation, then removes the namespace, then lets the session refetch
resolve the new branding. Doing the removal *before* the session settles is deliberate: a frame
rendered from the old context's cache is precisely what FR-087 forbids.

## 10. Zod schemas added

| Schema | Slice | Mirrors | Rules |
|---|---|---|---|
| `joinRegistrationSchema` | `features/join/register` | `JoinRegistrationRequest` | email ≤320; names 1–100; password ≥12 and ≤128 with confirmation; phone parseable; `player_name` required when `is_self` is false and `null` when true; `date_of_birth` a past date whose derived age is ≥18 when `is_self`, else 1–18; `gender` one of four |
| `brandingSchema` | `features/trainer/branding` | `PortalBrandingUpdate` | `primary_color` matches `^#[0-9a-fA-F]{6}$` or is null |
| `rosterSearchSchema` | `entities/trainer-context` | roster query parameters | `page`, `page_size` ≤100, `q` ≤200, all `.catch(...)` as in §1 |

`joinRegistrationSchema` is a Zod refinement across two fields rather than two independent field
rules, because the age band depends on `is_self` — the same coupling FR-077 states. The refinement
attaches its message to `date_of_birth`, so it renders beside the field the person can act on rather
than at form level.

The two server-only constraints from §3 still apply here: email uniqueness and breached-password
membership arrive as 422 field errors and are not duplicated client-side.

## 11. State ownership — where the trainer context lives

The active trainer context is **server state**. It arrives on `GET /auth/session` as
`active_trainer_id`, is owned by TanStack Query like every other server value, and is changed only
by the `switchTrainerContext` mutation.

It does **not** go in the Zustand store, and this is the temptation worth naming: it looks like UI
state — a dropdown selection that changes what the page shows. It is not. It persists across devices
(FR-086), the server enforces it as an isolation boundary (FR-087, R-25), and a copy in a store
would be a second source of truth for a value the server can correct underneath the client when the
active trainer becomes unavailable (FR-089). The store's rule from §4 is unchanged: nothing that
came from an API response goes in it.

`UiState` gains one field, and it is genuinely UI:

```ts
interface UiState {
  // ... existing fields unchanged ...
  isContextSwitcherOpen: boolean   // whether the dropdown is open. Nothing else.
}
```

**Owned by the URL** gains the roster's `page`, `page_size`, and `q`, for the same reasons the
directory's are there.

## 12. Branding: one provider, one derivation

```
shared/lib/brand-palette.ts     # pure: primary hex → CSS custom property values
widgets/branding-provider/      # reads session.portal_branding, sets the properties
```

The provider sets CSS custom properties on a wrapper element, overriding the defaults that
`app/styles/globals.css` derives from `DESIGN_TOKENS.md`. Components keep using the token names they
already use — no component reads `primary_color`, and no component holds a hex literal, which is
what keeps the constitution's design-token rule intact while the colour comes from data.

`brandPalette(primaryHex)` returns the accent colour unchanged for borders, gradient stops, and focus
rings, and returns *lightness-adjusted* variants for any surface that carries text, walking until the
token foreground clears a 4.5:1 contrast ratio (R-29, FR-099, SC-023). It is a pure function of one
string, so SC-023 is a unit test over a colour sweep rather than a visual review.

It mounts in two places — inside `routes/_authed.tsx` for signed-in people and inside
`routes/join.$code.tsx` for the public join page, whose branding comes from the preview response
rather than the session. Everywhere else, including `/login` and `/set-password`, renders the
platform default (FR-101).

**Logos render through `<img>` only.** Never `<object>`, never `<embed>`, never inlined into the DOM.
An SVG loaded as an image cannot execute script in any current browser, and that is the layer of
R-27's defence that holds even if the server-side screening is wrong. `resolveMediaUrl` from §5
handles branding URLs exactly as it handles photo URLs — they are API-relative for the same reason.

## 13. The context switcher

Lives in `widgets/app-shell`, beside the identity block, and renders only when the session reports
`trainer_count > 1` (FR-088). It reads `userKeys.trainers`, shows each trainer's logo and name, and
on selection calls `switchTrainerContext`, awaits it, clears the `ctx` namespace, and stays put —
there is no navigation, because the current route is valid in every context.

A player with `trainer_count === 0` sees no switcher and an empty state in place of context content,
which is the valid-but-unusual case R-24 keeps the nullable column for.

## 14. What the frontend must not infer — extended

| Value | Source | Why not computed locally |
|---|---|---|
| `viewer.state` on the join page | `GET /join/{code}` | Depends on the caller's role *and* their existing associations. Inferring it client-side means fetching the association list before a public page can render, and getting the four-way branch subtly wrong. |
| `active_trainer_id` | `GET /auth/session` | The server repairs a stale or dangling context on read (R-24, FR-089). A locally remembered value would survive its own trainer's deactivation. |
| `trainer_count` | `GET /auth/session` | Deciding whether to show the switcher from a cached list length shows a stale switcher for one frame after an association changes. |
| `portal_branding` | `GET /auth/session`, or the join preview | Which trainer's branding applies is FR-101's rule, and it differs by role. One resolution, server-side. |
