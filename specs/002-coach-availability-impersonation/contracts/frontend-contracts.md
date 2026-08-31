# Frontend Contracts: Coach Invitations, Availability & Impersonation

**Feature**: `002-coach-availability-impersonation` | **Date**: 2026-08-28

**Relationship to feature 001's contracts**: this file is additive. Everything in
`specs/001-user-roles-admin/contracts/frontend-contracts.md` §1 – §21 stands unchanged — the route
table, the query-key factory's shape, the state-ownership rules, the single axios instance, and the
"what the frontend must not infer" list all continue to apply. Sections here are numbered from
**§30** so no reference is ambiguous, and every rule below is an instance of a rule that file already
established rather than a new policy.

**Section index**

| § | Subject |
|---|---|
| §30 | Routes added |
| §31 | Query keys added |
| §32 | Zod schemas added |
| §33 | State ownership — the week editor, the banner, the toast |
| §34 | The availability week: one model, one formatter, two owners |
| §35 | The impersonation banner and the effective-identity rule |
| §36 | Navigation entries added |
| §37 | Types added to `shared/api/types.ts` |
| §38 | What the frontend must not infer — extended |

---

## §30 Routes added

All under TanStack Router's file-based convention, typed params and search only — no URL is ever built
from a string (Principle IV).

| Path | File | Access | Purpose |
|---|---|---|---|
| `/coach-invite/$token` | `src/routes/coach-invite.$token.tsx` | Public | Preview a coach invitation, then register or sign in to accept (FR-011 – FR-014). The public sibling of `/join/$code` |
| `/trainer/coaches` | `src/routes/_authed/trainer/coaches.tsx` | Trainer | The Coaches section: roster, invitation list, and the invite form (FR-001 – FR-007, FR-020, FR-021) |
| `/trainer/coaches/$coachUserId` | `src/routes/_authed/trainer/coaches.$coachUserId.tsx` | Trainer | One coach: their profile summary and their full stated week, read-only (FR-034, FR-037) |
| `/my-times` | `src/routes/_authed/my-times.tsx` | Coach | The coach's own week editor (FR-024) |
| `/availability` | `src/routes/_authed/availability.tsx` | Player/Parent | The family's week editor, with the profile switcher choosing whose week (FR-025, FR-033) |
| `/admin/impersonations` | `src/routes/_authed/admin/impersonations.tsx` | Super Admin | The impersonation history, with its filters (FR-053, FR-054) |

Two things deliberately get **no** route of their own:

- **Starting an impersonation** is an action on a row of the existing `/admin/users` directory
  (FR-040), not a page. It opens a confirmation dialog and, on confirm, navigates to `/`.
- **A player's full week, seen by their trainer** lives on the existing
  `/trainer/players` row expansion rather than a new page, because the trainer's player record is
  already there and FR-034 asks for the times *on* the record.

`/trainer/players` and `/trainer/coaches` both render the summary from the slots embedded in their
list payload; neither fetches per row (§34).

---

## §31 Query keys added

Following the existing factory shape — a namespace tuple, then the parameters that identify the
resource, so an invalidation can be as narrow or as broad as the mutation warrants.

```ts
// entities/coach-invitation/api/query-keys.ts
export const coachInvitationKeys = {
  all: ['coach-invitations'] as const,
  list: (params: CoachInvitationListParams) => ['coach-invitations', 'list', params] as const,
  preview: (token: string) => ['coach-invitations', 'preview', token] as const,
}

// entities/coach/api/query-keys.ts
export const coachKeys = {
  all: ['coaches'] as const,
  roster: (params: CoachRosterParams) => ['coaches', 'roster', params] as const,
  detail: (coachUserId: string) => ['coaches', 'detail', coachUserId] as const,
}

// entities/availability/api/query-keys.ts
// One namespace, one discriminated subject — never two parallel key families, because the
// week is one concept with two kinds of owner (research.md R2-07).
export type AvailabilitySubject =
  | { kind: 'own' }
  | { kind: 'profile'; profileId: string }
  | { kind: 'coach-as-trainer'; coachUserId: string }
  | { kind: 'player-as-trainer'; profileId: string }

export const availabilityKeys = {
  all: ['availability'] as const,
  week: (subject: AvailabilitySubject) => ['availability', 'week', subject] as const,
}

// entities/impersonation/api/query-keys.ts
export const impersonationKeys = {
  all: ['impersonations'] as const,
  history: (params: ImpersonationHistoryParams) => ['impersonations', 'history', params] as const,
}
```

**Invalidation rules** (each mutation names exactly what it invalidates — no blanket
`queryClient.clear()` anywhere):

| Mutation | Invalidates |
|---|---|
| Issue / resend / revoke invitation | `coachInvitationKeys.all` |
| Accept invitation (on the public route) | `sessionKey` — the caller's role, trainer, and branding all changed |
| End coach assignment | `coachKeys.all`, and `availabilityKeys.all` because that coach's week is no longer disclosed |
| Save or clear a week | `availabilityKeys.week(subject)` only. A parent saving Leo's week must not refetch Grace's |
| Start impersonation | `sessionKey`, then **`queryClient.clear()`** — the only sanctioned use in the app (§35) |
| End impersonation | `sessionKey`, then `queryClient.clear()`, same reason |

---

## §32 Zod schemas added

Every schema encodes exactly what the backend enforces, reading its bounds from one shared constants
module so the two cannot drift (research.md R2-21).

```ts
// entities/availability/model/week.ts
export const MINUTES_PER_SLOT_STEP = 15
export const MAX_SLOTS_PER_DAY = 6
export const MINUTES_IN_DAY = 1440

export const availabilitySlotSchema = z.object({
  day_of_week: z.number().int().min(0).max(6),
  start_minute: z.number().int().min(0).max(MINUTES_IN_DAY - MINUTES_PER_SLOT_STEP)
    .refine((m) => m % MINUTES_PER_SLOT_STEP === 0),
  end_minute: z.number().int().min(MINUTES_PER_SLOT_STEP).max(MINUTES_IN_DAY)
    .refine((m) => m % MINUTES_PER_SLOT_STEP === 0),
}).refine((s) => s.start_minute < s.end_minute, { path: ['end_minute'] })

// The two set-level rules the backend applies to the whole week (FR-027, FR-028) —
// per day, at most six ranges, and no overlaps; touching ranges are valid.
export const availabilityWeekSchema = z.object({
  slots: z.array(availabilitySlotSchema).max(MAX_SLOTS_PER_DAY * 7),
}).superRefine(validateWeek)   // issues are attached to the offending day's path
```

```ts
// entities/coach-invitation/model/invitation.ts
export const coachInvitationCreateSchema = z.object({
  email: z.string().email().max(320),
  // Optional text fields are typed as string here because a controlled input yields "";
  // the shared normalizer in shared/lib/normalize-payload.ts turns "" into null before the
  // payload reaches axios (Principle VI). No inline ternary at the call site.
  invitee_name: z.string().max(200),
  message: z.string().max(2000),
})
```

```ts
// entities/impersonation/model/history-search.ts — URL-owned filters, with .catch() fallbacks
export const impersonationHistorySearchSchema = z.object({
  page: z.number().int().min(1).catch(1),
  page_size: z.number().int().min(1).max(100).catch(25),
  admin_user_id: z.string().uuid().optional().catch(undefined),
  target_user_id: z.string().uuid().optional().catch(undefined),
  started_from: z.string().datetime().optional().catch(undefined),
  started_to: z.string().datetime().optional().catch(undefined),
})
```

The history filters live in the URL, exactly as the user directory's search does, so a compliance
answer is a shareable link.

---

## §33 State ownership — the week editor, the banner, the toast

| State | Owner | Why |
|---|---|---|
| The stored week for any subject | TanStack Query, `availabilityKeys.week(subject)` | Server state. Never copied into Zustand |
| The week being edited, before save | TanStack Form (one form per week) | Form state, discarded on cancel |
| Which profile's week a parent is editing | The existing training-context / profile switcher selection, read from the session query | A second source for "whose data am I looking at" is how a sibling's week gets saved onto the wrong profile |
| Whether an impersonation is live, and its target | TanStack Query, `sessionKey` — the `impersonation` block on `CurrentUser` | Server state, and the server is the only authority on it (§35) |
| Which end-of-impersonation notices have been shown | Zustand, a small UI slice keyed by impersonation id | Client UI state — "have I shown this toast" — which is exactly what the constitution reserves Zustand for (research.md R2-20) |
| The invite-coach dialog's open/closed state | Zustand or local component state | Modal state |

The week editor holds **one** form for the whole week, not one per day and not one per range. The
backend replaces the week atomically (FR-029), so a per-day form would let a user save three of five
days and believe the other two were saved.

---

## §34 The availability week: one model, one formatter, two owners

The single most important frontend rule in this feature: **there is one week model, one editor widget,
and one formatter**, used by both the coach's My Times page and the family's Availability page, and by
both trainer-side read views.

```
entities/availability/
  model/week.ts            — types, Zod schema, set-level validation (§32)
  model/format-summary.ts  — slots → "Mon 5–8pm, Wed 6–9pm" and slots → full-week rows
  api/use-availability.ts       — one hook, taking an AvailabilitySubject (§31)
  api/use-save-availability.ts  — one mutation, taking the same subject
features/availability/
  ui/availability-week-editor.tsx   — the editor; owner-agnostic
  ui/availability-week-view.tsx     — the read-only week; owner-agnostic
  ui/availability-summary.tsx       — the one-line summary used in list rows
```

`format-summary.ts` is the only place a day name, a 12-hour clock, or an en-dash appears. The API
returns structured minutes and never a pre-baked string (research.md R2-12), so the summary in a
roster row and the heading of a full-week view cannot disagree.

Three rendering rules the formatter owns, all of them requirements rather than taste:

- `updated_at === null` renders as **"No times set"**, never as "Unavailable" (FR-035).
- `updated_at !== null` with no slots renders as **"No times set"** too, with the revision date
  beside it — a person who cleared their week has stated something, and the date says when.
- A day with no ranges is absent from the summary rather than listed as "Not available", so the
  summary stays short; the full-week view shows every day and marks the empty ones.

---

## §35 The impersonation banner and the effective-identity rule

**The rule**: while an impersonation is live, `GET /auth/session` describes the *impersonated person*
(FR-043). Every existing hook, guard, nav item, and page therefore renders that person's portal with
no change whatsoever — which is the entire point of the server-side design (research.md R2-14). The
frontend adds exactly three things:

1. **`widgets/impersonation-banner`** — rendered by `routes/_authed.tsx` above `AppShell`, so it is
   present on every authenticated view (FR-044). Reads `session.impersonation`; renders nothing when
   it is `null`. Visually distinct through the design tokens' destructive/warning role, never an
   ad-hoc hex value (constitution: design tokens). It shows the impersonated person's name, the
   acting admin's name, a live countdown to `expires_at`, and an Exit control.
2. **`features/admin/impersonation`** — the Impersonate action on a user-directory row, its
   confirmation dialog naming the person and role (FR-040), and the mutations that start and end an
   impersonation.
3. **A toast for `session.impersonation_ended`**, shown once per impersonation id, deduplicated in
   the Zustand slice of §33 (FR-046).

**`queryClient.clear()` on both boundaries.** Starting and ending an impersonation are the only two
places in the application permitted to clear the whole query cache, and they must: every cached
response belongs to the previous identity, and showing a Super Admin's cached directory page inside a
Trainer's portal would be a data-isolation failure produced entirely on the client. Both mutations
therefore `await queryClient.clear()` and then navigate to `/`.

**Nothing about impersonation is inferred client-side.** The banner does not compute whether the
session is impersonated from role mismatches, and the countdown is display only — when it reaches
zero, the next server response is what ends the impersonation (FR-046, research.md R2-19). A client
timer that ended it locally would be a lie the moment the tab was asleep.

**Route guards stay as they are.** `_authed.tsx` and the role-guarded pages keep their existing logic;
because the effective user *is* the impersonated person, a Super Admin impersonating a Trainer is
redirected away from `/admin/users` by the same guard that redirects any trainer — correct behaviour,
achieved with no impersonation-specific code (FR-043).

---

## §36 Navigation entries added

`widgets/app-shell/model/use-nav-items.ts` gains four entries, and the `NavItem` union gains four
members. The file's existing comment — "`coach` deliberately resolves to an empty list: this feature
gives it no dedicated page" — is corrected: the coach now has one.

| Role | Entry | Path | Requirement |
|---|---|---|---|
| Coach | "My Times" | `/my-times` | FR-024 |
| Trainer | "Coaches" | `/trainer/coaches` | FR-020 |
| Player/Parent (parent **and** child) | "Availability" | `/availability` | FR-025, FR-033 |
| Super Admin | "Impersonation history" | `/admin/impersonations` | FR-053 |

The Player/Parent entry is shown to a signed-in child as well as to a parent — unlike Approvals and
Requests, which are filtered by `isChildAccount`. A child may state their own times (FR-033), so
withholding the entry would hide a capability they have.

Every entry is rendered through the existing per-case `switch` in `PrimaryNav` and `CrumbLink`, adding
one branch each, for the reason those switches exist: each route's `to`/`params`/`search` combination
stays checked against the exact overload TanStack Router expects (no `any`).

---

## §37 Types added to `shared/api/types.ts`

Mirroring the Pydantic schemas one-for-one (Principle II boundary parity). Optionality is spelled
`| null`, never `?`, for every field the backend declares nullable — an absent optional value is
`null` at every layer (Principle VI).

```ts
export interface AvailabilitySlot { day_of_week: number; start_minute: number; end_minute: number }
export interface AvailabilityWeek { slots: AvailabilitySlot[]; updated_at: string | null }

export type CoachInvitationPresentedState =
  | 'awaiting' | 'accepted' | 'expired' | 'revoked' | 'blocked'
export type CoachInvitationBlockReason = 'role_not_coach' | 'already_assigned'
export interface CoachInvitation { /* … as contracts/openapi.yaml CoachInvitation */ }
export interface CoachInvitationPreview { /* … */ }
export interface TrainerCoachSummary { /* … includes availability: AvailabilitySlot[] */ }

export type ImpersonationEndReason =
  | 'exited' | 'timed_out' | 'signed_out' | 'superseded'
  | 'target_deactivated' | 'target_erased' | 'admin_deactivated'
export interface Impersonation { /* … as contracts/openapi.yaml Impersonation */ }
```

`CurrentUser` gains two fields, both `Impersonation | null`: `impersonation` and
`impersonation_ended`. `TrainerPlayerSummary` gains `availability: AvailabilitySlot[]` and
`availability_updated_at: string | null`.

The doc comment on `CurrentUser.portal_branding` — "Coaches receive the default until US-01.08" — is
corrected: a coach on a roster now receives their trainer's branding (research.md R2-06).

---

## §38 What the frontend must not infer — extended

Adding to feature 001's list. Each of these is a fact only the server may state:

- **Whether an invitation is usable, expired, or blocked.** The server sends the presented state
  (data-model.md §101.1); the client renders it. A client that compared `expires_at` to the browser
  clock would disagree with the server across a timezone or a slow clock.
- **Whether a coach may accept.** The one-trainer rule, the address binding, and the role check are
  server refusals with their own codes; the client shows the message it is given. It must not
  pre-empt them, because it cannot know what other roster a coach is on — and must not be told.
- **Which trainer a blocked coach already works for.** Not in any payload, and not to be guessed at
  or hinted in copy (FR-015, FR-019).
- **Whether a person is "available".** Only "these are the times they stated" and "they have stated
  none". The client never renders a person as unavailable, and never uses stated times to disable a
  control — availability gates nothing (FR-038).
- **Whether an impersonation is live or has expired.** Read from `session.impersonation`; the
  countdown is decoration.
- **Whose data is on screen during an impersonation.** The session response is authoritative. The
  client must not layer an "as yourself" override on any view.
