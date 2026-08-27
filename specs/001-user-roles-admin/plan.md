# Implementation Plan: User Roles, Super Admin Management, ShareLink Onboarding & Portal Branding

**Branch**: `001-user-roles-admin` | **Date**: 2026-08-19, extended 2026-08-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-user-roles-admin/spec.md`

## Summary

Build the foundation of Epic-01: a four-role account model with three lifecycle statuses, email and
password sign-in with server-side sessions, permission enforcement on every request, and the Super
Admin user directory through which accounts are created, deactivated, reactivated, and privacy-erased.
Every signed-in person can edit their own profile, including the fields specific to their role.

The technical approach is a FastAPI service over async SQLAlchemy and SQLite, layered strictly as
router → service → repository, paired with a React and Vite frontend organized by Feature-Sliced
Design. Two decisions shape most of the design: sessions are **opaque server-side tokens** rather than
JWTs, because FR-012 demands that deactivation revoke access immediately; and privacy erasure
**anonymizes the account row in place** rather than deleting it, because FR-046 and FR-047 demand that
history and reporting totals survive an erasure untouched. Both are argued in
[research.md](./research.md) R-03 and R-08.

Delivery follows the spec's story priorities, each slice independently demonstrable: sign-in and
permissions (P1), account creation and invitation (P1), profile self-service (P2), deactivation (P2),
erasure (P3).

**The 2026-08-26 extension** adds three further slices — joining a trainer through a ShareLink (P1),
multi-trainer association with server-resolved context (P2), and trainer portal branding (P3). Its
Technical Context, Constitution Check, structure, sequence, and recorded judgements are in
[§Extension](#extension-2026-08-26-sharelink-onboarding-multi-trainer--portal-branding) at the end of
this document; everything above it describes the already-implemented foundation and is unchanged.

**The 2026-08-27 extension** adds family accounts: one account holding several players (P1), the
parent's control over each child's trainers (P1), a child's own constrained sign-in (P2), the Pending
Parent Approval workflow (P2), and the family-member selection prompt when a parent joins a new
trainer (P3). It is the first extension that **changes structures the earlier slices already
implemented** — a trainer association moves from naming an account to naming a player profile — and
it is planned in
[§Extension (2026-08-27)](#extension-2026-08-27-family-accounts-child-sign-in--the-approval-workflow).

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript 5.7 in `strict` mode (frontend)

**Primary Dependencies**:

| Concern | Choice | Note |
|---|---|---|
| API framework | FastAPI | Constitution-locked |
| ORM | SQLAlchemy 2.0, async | Constitution-locked; `Mapped`/`mapped_column` style |
| Driver | `aiosqlite` | Async SQLite (R-12) |
| Validation | Pydantic V2 | Constitution-locked |
| Configuration | `pydantic-settings` | Constitution-locked |
| Migrations | Alembic (async template) | Required by constitution's migration rule (R-13) |
| Password hashing | `pwdlib[argon2]` | Argon2id; `passlib` rejected (R-04) |
| Images | Pillow | Decode-validation and thumbnails (R-07) |
| Email | `aiosmtplib` + a filesystem sink | Two implementations behind one port (R-11) |
| Frontend build | Vite, React 19 | Constitution-locked |
| Routing | TanStack Router, file-based | Typed params and Zod search params (R-19) |
| Server state | TanStack Query | Constitution-locked |
| Forms | TanStack Form v1 (`@tanstack/react-form` 1.33.x) | With Zod adapter (R-19) |
| Client state | Zustand | UI state only, one small store |
| Styling | Tailwind CSS v4 via `@tailwindcss/vite`, shadcn/ui, `tw-animate-css` | CSS-first config (R-18) |
| HTTP client | axios | One instance in `shared/api` |
| Charts | Chart.js | **Not used in this feature** — no dashboard visualization in scope |

**Storage**: SQLite via `aiosqlite`, foreign keys enabled and WAL journaling set per connection.
Profile photos on the local filesystem behind a storage port. Both are single-host choices matching
this feature's scale, isolated behind the repository and port boundaries so the eventual moves to
PostgreSQL and object storage are configuration and migration work rather than rewrites.

**Testing**: pytest with `pytest-asyncio` for unit and service tests; `httpx` over `ASGITransport`
for integration tests against a temporary migrated SQLite file; a contract test asserting the
generated OpenAPI document against `contracts/openapi.yaml`; Vitest with React Testing Library and MSW
on the frontend (R-20).

**Target Platform**: Linux or Windows host running a single ASGI process; frontend is a static bundle
served by the same origin so the session cookie stays first-party.

**Project Type**: Web application — separate backend service and frontend application in one
repository.

**Performance Goals**: Sign-in to landing area under 2 s (SC-001); directory first page under 3 s at
10,000 accounts (SC-006); profile save under 1 s for non-photo fields (SC-005). These are modest, and
the design meets them through indexed, paged queries rather than caching. The one query that must not
regress is the directory's filtered page, which is why `(status, role)` and `created_at` are indexed
and `page_size` is capped at 100.

**Constraints**: SQLite permits a single writer, so administrative writes serialize — comfortable at
this feature's write volume and stated plainly rather than hidden. No `any` anywhere in the frontend.
No raw SQL except the two documented exceptions below. Sessions must be revocable within one minute
(SC-007), which the design satisfies synchronously.

**Scale/Scope** (foundation, as built): 10,000 accounts as the directory performance target; four
roles; 19 API operations; 9 database tables; 5 frontend routes plus two layout routes; 56 functional
requirements. After the 2026-08-26 extension: 33 API operations, 12 database tables, nine routes plus
three layout routes, 104 functional requirements — see §Extension.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.0. **Re-evaluated against v1.1.0 on
2026-08-25** during the bug-fix slice; the added Principle VI row below is the result, and it is the
one row that did not pass.

| Principle | Requirement | Pre-Phase-0 | Post-Phase-1 | How the design satisfies it |
|---|---|:---:|:---:|---|
| I. Spec-Driven Development | Spec → Plan → Tasks → Code; no code before approval | PASS | PASS | `spec.md` approved; this plan and its artifacts contain no functional code. `tasks.md` comes next; implementation only after. |
| II. End-to-End Type Safety | No `any`; Pydantic V2 everywhere; boundary parity | PASS | PASS | Role detail is a discriminated union, not a JSON blob (R-15), so narrowing uses type guards. Zod-to-Pydantic parity is tabulated in `contracts/frontend-contracts.md` §3. `unknown` plus `isApiError` is the single narrowing point for errors. |
| III. Layered Backend Architecture | Router → service → repository; `Depends`; no global state | PASS | PASS | Directory tree below assigns one layer per package. Role gate is a dependency; state-dependent rules are in services; all queries in repositories (R-14). Settings and sessions are injected, never module-level. |
| IV. Feature-Sliced Frontend | FSD layers, one-way imports, `shared/ui`, `shared/api`, Query for server state, Zustand for UI only | PASS | PASS | Layer mapping in R-17; state ownership fixed in `contracts/frontend-contracts.md` §4. The Zustand store holds three UI fields and `pendingAction` deliberately stores a `userId`, not an account object. |
| V. Async-First & Contained Failures | Async I/O, `AsyncSession`, no raw SQL, service-layer error translation | PASS | **PASS with 2 documented exceptions** | Every I/O path is `async`. Domain errors raised in services map to `HTTPException` in routers through one handler; the single `Error` envelope in the contract carries no internal detail (FR-056). The two raw-SQL exceptions are recorded in Complexity Tracking. |
| VI. Null-Not-Empty Data Contract | One shared empty-string→null normalizer in `shared/lib`; nullable Pydantic fields are `str \| None` with `min_length=1`; an explicit null clears the column | n/a (added in v1.1.0) | **FAIL as built — remediated by the Fix phase** | As built the frontend had **no** normalizer, so `''` crossed the boundary for every optional profile field; 11 nullable fields in `OwnProfileUpdate` carried no `min_length=1`, so `''` reached the database; and `first_name`/`last_name` accepted an explicit `null` against `NOT NULL` columns, surfacing as a 500. tasks.md T157 and T163–T170 close all three, and T196 adds the grep gate that keeps them closed. This also discharges the constitution's standing `TODO(NULL_NORMALIZATION_HELPER)`. |
| Stack constraints | Fixed stack; config via `pydantic-settings`; design tokens; versioned migrations | PASS | PASS | No dependency outside the locked list except the four the locked choices require (`aiosqlite`, `pwdlib`, Pillow, `aiosmtplib`) and Alembic, which the constitution's own migration rule mandates. Tokens from `DESIGN_TOKENS.md` become CSS custom properties (R-18). Four Alembic revisions (data-model §13). Chart.js is in the locked stack but unused here, which the stack rule permits — it forbids additions, not non-use. |
| Workflow & quality gates | Type checking, lint, tests, no `any`, FSD import direction | PASS | PASS | Gate commands are listed in `quickstart.md` §6 so `tasks.md` can attach them per slice. |

**Gate result: PASS.** No unjustified violations. The two raw-SQL exceptions are narrow, argued, and
recorded below rather than waived.

## Project Structure

### Documentation (this feature)

```text
specs/001-user-roles-admin/
├── plan.md                          # This file
├── spec.md                          # Approved specification
├── research.md                      # Phase 0 — 33 decisions, both clarifications resolved
├── data-model.md                    # Phase 1 — 12 tables, transitions, erasure mapping
├── quickstart.md                    # Phase 1 — setup and story-by-story validation
├── contracts/
│   ├── openapi.yaml                 # Phase 1 — 33 operations, 37 schemas
│   └── frontend-contracts.md        # Phase 1 — routes, query keys, state ownership
├── checklists/
│   └── requirements.md              # Spec quality checklist — all items pass
└── tasks.md                         # Phase 2 — created by /speckit-tasks, not by this command
```

### Source Code (repository root)

```text
backend/
├── src/app/
│   ├── main.py                      # App factory, router registration, exception handlers
│   ├── core/
│   │   ├── config.py                # pydantic-settings Settings; injected, never global
│   │   ├── security.py              # Argon2id hashing, token generation, password policy
│   │   ├── errors.py                # Domain error hierarchy + HTTP translation map
│   │   └── deps.py                  # Depends providers: session, current user, role gate
│   ├── db/
│   │   ├── engine.py                # Async engine; PRAGMA setup on connect (exception 1)
│   │   ├── session.py               # Per-request AsyncSession provider
│   │   └── base.py                  # DeclarativeBase
│   ├── models/                      # SQLAlchemy models — one module per table group
│   │   ├── user.py                  # users, user_profiles
│   │   ├── role_details.py          # trainer_organizations, coach_details, player_details, parent_contacts
│   │   ├── auth.py                  # sessions, credential_setup_invitations, sign_in_attempts
│   │   └── audit.py                 # audit_entries, erasure_records
│   ├── schemas/                     # Pydantic V2 request/response models
│   │   ├── auth.py
│   │   ├── profile.py
│   │   ├── admin_user.py
│   │   └── common.py                # Error envelope, page wrapper
│   ├── repositories/                # ALL database access
│   │   ├── user_repository.py
│   │   ├── session_repository.py
│   │   ├── invitation_repository.py
│   │   ├── sign_in_attempt_repository.py
│   │   ├── audit_repository.py      # insert + select only — no update/delete method exists
│   │   └── erasure_repository.py
│   ├── services/                    # ALL business logic
│   │   ├── auth_service.py          # sign-in, rate limit, session lifecycle, password setup
│   │   ├── profile_service.py       # own-profile read/update, editable-field rules
│   │   ├── user_admin_service.py    # create, deactivate, reactivate, reinvite, directory
│   │   ├── erasure_service.py       # anonymization transaction + compliance record
│   │   └── ports/
│   │       ├── email_sender.py      # Protocol + SMTP and filesystem-sink implementations
│   │       └── photo_storage.py     # Protocol + local filesystem implementation
│   └── api/v1/
│       ├── auth_router.py
│       ├── me_router.py
│       ├── admin_users_router.py
│       └── media_router.py
├── migrations/                      # Alembic; 4 revisions per data-model §13
├── tests/
│   ├── unit/                        # Services against fake repositories
│   ├── integration/                 # httpx + temporary migrated SQLite
│   └── contract/                    # Generated OpenAPI vs contracts/openapi.yaml
├── pyproject.toml
└── .env.example                     # Every required key, no secrets

frontend/
├── src/
│   ├── app/                         # Entry, providers, router registration, Tailwind entry CSS
│   │   ├── main.tsx
│   │   ├── providers/               # QueryClient, router, theme
│   │   ├── store/ui-store.ts        # The one Zustand store — UI state only
│   │   └── styles/globals.css       # Tailwind v4 CSS-first config + DESIGN_TOKENS properties
│   ├── pages/                       # Route components
│   │   ├── login/
│   │   ├── set-password/
│   │   ├── dashboard/
│   │   ├── profile/
│   │   └── admin-users/
│   ├── widgets/
│   │   ├── user-directory-table/
│   │   └── profile-form-shell/
│   ├── features/
│   │   ├── auth/{sign-in,set-password,sign-out}/
│   │   ├── profile/edit-own/
│   │   └── admin/{create-user,deactivate-user,reactivate-user,erase-user,reinvite-user}/
│   ├── entities/
│   │   ├── user/{api,model,ui}/      # Query hooks, query-key factory, types, role guards
│   │   └── session/{api,model}/      # Current-session query, role predicates
│   ├── shared/
│   │   ├── api/                      # THE axios instance, interceptors, ApiError
│   │   ├── ui/                       # ALL shadcn/ui primitives live here
│   │   ├── lib/                      # Formatters, type guards
│   │   └── config/                   # Runtime config, route constants
│   └── routes/                       # TanStack Router file-based route tree
├── tests/                            # Vitest + RTL + MSW
├── vite.config.ts
├── tsconfig.json                     # strict; noUncheckedIndexedAccess
└── components.json                   # shadcn/ui → shared/ui path mapping
```

**Structure Decision**: A two-package web application — `backend/` and `frontend/` — because the
constitution mandates a Python API and a separate React SPA, which cannot share a source tree.

Inside `backend/src/app`, the package names *are* the constitution's layers: `api/` holds routers and
nothing else, `services/` holds business logic and never touches `Request`, `repositories/` holds every
query and no business rule. A reviewer can check layering by looking at import direction between three
directories rather than reading for it.

The frontend tree is the FSD layer list verbatim, with one deliberate omission: **`processes/` is not
created.** FSD treats it as optional and now discourages it, and this feature has no cross-page flow —
the set-password journey is one page reached by a link. Creating an empty directory to match a list
would be cargo cult; the layer arrives with the first slice that needs it. `shared/ui` is the only
home for shadcn/ui components, and `components.json` is configured so the shadcn CLI generates
directly into it rather than a default `components/ui` path — otherwise the constitution's UI rule
would be violated by the tooling on every `add` command.

## Implementation Sequence

Aligned to the spec's story priorities; each phase is independently demonstrable, matching each
story's Independent Test.

| Phase | Delivers | Backend | Frontend | Proves |
|---|---|---|---|---|
| 0 | Skeleton | App factory, settings, engine with PRAGMAs, revision 1, error handler | Vite, Tailwind v4, shadcn/ui, axios instance, Query client, router | Both apps start; migrations run |
| 1 | **US1** — sign-in and permissions | Models, revisions 1–4, hashing, sessions, rate limiting, role gate, `/auth/*`, bootstrap Super Admin command | Login page, session query, route guards, per-role landing | SC-001, SC-002, SC-011, SC-012 |
| 2 | **US2** — create and invite | `POST /admin/users`, invitation issue and consume, `/auth/setup-password*`, reinvite, email port, audit on create | Create-user form, set-password page, directory list | SC-003, SC-004, SC-010 |
| 3 | **US3** — own profile | `/me/profile`, photo upload with decode-validation and thumbnails, `/media/photos`, role detail read/write rules | Profile page, per-role form via discriminated schema, photo control | SC-005 |
| 4 | **US4** — deactivate and reactivate | Status transitions, transactional last-admin guard, session revocation, version check | Directory actions, confirmation dialogs, inactive marking | SC-007, SC-008 |
| 5 | **US5** — erasure | Anonymization transaction, compliance record, photo file removal, erasure record endpoint | Erasure dialog with reason capture, post-erasure view | SC-009 |
| 6 | Hardening | Contract test, permission matrix test across all roles and routes, pruning routine, `.env.example` | Accessibility pass, error-state coverage | Full suite green |

Phase 1 carries the whole data model rather than adding tables per phase: the four revisions are one
schema, and splitting them across phases would mean migrations that exist only to be superseded.

## Complexity Tracking

Two deviations from the constitution's **No Raw SQL** rule. Both are recorded rather than waived, and
both are confined to migration or engine-configuration code that takes no user input.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Literal `PRAGMA` statements on connection setup (`foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout`) in `db/engine.py` | SQLite does not enforce foreign keys unless instructed per connection, and this design relies on those keys to hold history to accounts (R-08, R-12). WAL lets the read-heavy directory proceed during administrative writes. | No ORM or Core construct expresses `PRAGMA`; SQLAlchemy's own documented approach is a connection event emitting the literal statement. Omitting the pragmas is the only alternative, and it silently disables the referential integrity the erasure design depends on. Contained to one function, parameterless, no user input. |
| `CREATE TRIGGER` DDL in Alembic revision 4, raising on `UPDATE`/`DELETE` against `audit_entries` | FR-055 requires that no one can alter or remove an audit entry through the platform. The repository having no mutation method makes the *application* incapable; the trigger closes the path where a later migration or script bypasses the repository. | Application-level enforcement alone was considered and is the primary control — the trigger is defence in depth for an append-only legal record. A trigger is not expressible as an ORM or Core construct. It lives in a versioned revision, so it is reviewed like any other schema change. |

Neither exception touches request handling, and no service or repository issues raw SQL. Every query
in the feature is an ORM or Core construct, as Principle V requires.

**One further judgement recorded for review** (not a constitution violation, but a decision a reviewer
should see rather than discover): erasure leaves `trainer_organizations.business_name` and
`player_details.skill_level` intact, because FR-047 requires reporting totals and organizational
attribution to survive. For a sole trader whose business name is their own name, this retains personal
data. The reasoning and the one-line fallback are in [data-model.md](./data-model.md) §10, and the
spec already flags the related email-retention question for legal review.

## Post-Implementation Technical Decisions (Bug-Fix Slice)

Six defects were reported after Phases 1–8 landed (tasks.md §Fixes, F1–F6). The decisions below
resolve them. None changes an architectural principle; each fills a gap the original plan left
implicit, which is why the defect was possible.

### D-01 — Optional values: one normalizer, and `min_length=1` everywhere (F1)

Exactly one helper, `frontend/src/shared/lib/normalize-payload.ts`, converts empty and
whitespace-only strings to `null`, recursing through nested objects and arrays and passing every
other value through untouched. Every TanStack Form submit handler routes its payload through it
before `axios` sees it. Trimming of real values stays in the field's Zod schema, never in the
normalizer. Per-form ternaries and a second helper are forbidden — Principle VI says one.

On the server, every nullable string field carries `min_length=1` so `''` is a 422 rather than a
stored value, and the two required name fields reject an explicit `null` with a field-attributed 422
instead of reaching a `NOT NULL` column and surfacing as a 500. Services keep reading
`model_dump(exclude_unset=True)`, so an omitted key leaves its column untouched while an explicit
`null` clears it — the distinction Principle VI exists to preserve, and the one the frontend could
not previously express because it sent `''` for both.

**Rejected**: normalizing inside the axios request interceptor. It would catch every payload
automatically, which is its appeal, but it would also silently rewrite bodies for callers that want
`''` preserved, and it hides a data-contract rule inside transport plumbing where no reviewer looks.

### D-02 — Validation timing: submit first, then live (F5, FR-057)

`@tanstack/react-form` 1.33.5 ships `revalidateLogic`, so this needs no hand-rolled flag: every form
uses `validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' })` with its
Zod schema moved from `validators: { onChange }` to `validators: { onDynamic }`. Before the first
submit nothing validates; after it, fields revalidate live as they are corrected. The submit button
drops `canSubmit` from its `disabled` expression and keeps only `isSubmitting`, because a button
disabled by invisible errors is how FR-057's second sentence gets violated.

Field errors render through one shared `fieldErrorText` helper that normalizes both Standard-Schema
issue objects and plain strings — the previous inline
`errors.map((e) => e?.message).join(', ')` silently rendered nothing for a string error, which is
half of why server-side messages never appeared. Server 422 field errors are injected with
`form.setErrorMap({ onServer: toServerErrorMap(error) })`, the library's supported channel, so
FR-058 holds for both sources of rejection with one mapping rather than one per form.

### D-03 — Media URLs are assembled by the client (F2, FR-060)

`photo_url` and `thumbnail_url` stay **API-relative** (`/media/photos/{key}`). The service layer must
not learn the API's HTTP mount prefix — that is a router concern, and Principle III keeps it out of
services. The client therefore assembles the absolute URL in one place,
`frontend/src/shared/api/media.ts`, which prefixes the axios `baseURL`. Requests made *through*
axios already resolved correctly; only DOM `src` attributes did not, because the browser resolves
them against the document origin instead. That single omission is the whole defect.

**Rejected**: returning `/api/v1/media/photos/...` from the service. It fixes the symptom by putting
the mount prefix in three service methods, so any change to the prefix becomes a data-shaped change.

### D-04 — Directory search: 500 ms, URL-owned, replace-navigated (F4, FR-063, SC-013)

The typed term is held in local component state seeded from the `q` search param and pushed into the
URL after **500 ms** of inactivity (interval chosen by the user on 2026-08-25). The URL remains the
single source of truth for `q`, per `contracts/frontend-contracts.md` §4 — no Zustand field, no
second copy of the term. Search-term navigation uses `replace: true` so a 20-character query leaves
one history entry rather than twenty; paging and the role and status filters keep pushing a normal
entry, because those are deliberate steps a Super Admin should be able to reverse.

At 500 ms the directory issues one query per settled term instead of one per character, which is what
SC-013 measures. The interval is a tuning value, not a structural decision.

### D-05 — Navigation: a shared back control inside a persistent shell (F3, FR-061, FR-062, SC-014)

Two parts, both required — the user chose the shell in addition to the button on 2026-08-25.

A shared `BackButton` in `shared/ui` calls the router's `history.back()` when `useCanGoBack()` is
true and navigates to a required typed `fallbackTo` route otherwise, so a deep-linked page still
offers a way out. History-based back is what makes FR-061's "restore the filtered view" free: the
previous entry already carries the directory's search params, so nothing has to be threaded through
links. The hardcoded `<Link to="/admin/users">` it replaces discarded them.

A persistent shell, `widgets/app-shell`, renders the identity block, a breadcrumb trail derived from
the router's matched routes with typed link descriptors, the profile link, the sign-out action, and
the region the `BackButton` renders into. It mounts at **`routes/_authed.tsx`, not
`routes/__root.tsx`**: the root route also carries `/login` and `/set-password`, and signed-in chrome
on a sign-in page is what FR-062's last sentence forbids. The dashboard's hand-rolled header is
removed in the same change, or the landing page carries two.

### D-06 — Email: finish the SMTP port, add nothing (F6, FR-064)

R-11's design stands unchanged — one `EmailSender` port, an SMTP implementation, a filesystem sink
for development and tests, sent in-request with the failure surfaced to the Super Admin. **SMTP only:
no HTTP-API provider, no persisted outbox, no retry worker** (user decision, 2026-08-25). R-11
already argues why an outbox is premature for a single invitation, and a second transport would be a
second thing to configure and test for no behaviour gained.

What was missing is completed: `Settings` gains a `model_validator` making `SMTP_HOST` and
`SMTP_FROM_ADDRESS` mandatory when `EMAIL_BACKEND=smtp`, so a misconfigured relay is a startup
failure rather than every invitation silently reporting `invitation_sent: false`; `SMTP_TLS`
(`starttls` | `implicit` | `none`) and `SMTP_TIMEOUT_SECONDS` become configurable, because the
hard-coded STARTTLS could reach neither an implicit-TLS relay on 465 nor a local Mailpit on 1025, and
an unreachable relay could hang an in-request send indefinitely; and the hard-coded
`noreply@example.org` envelope fallback is removed, since a default that is wrong in production is
exactly what this plan's configuration rule forbids. On the client, the re-invite action stops
reporting success unconditionally and honours `invitation_sent`, which is what FR-064 requires and
what makes FR-028's recovery loop actually reachable.

### D-07 — One role-aware nav descriptor list, read by both the shell and the landing area (F7)

A seventh defect was reported on 2026-08-27: the extension's trainer pages are unreachable by
clicking. The fix is one list, not links scattered per page.
`widgets/app-shell/model/use-nav-items.ts` returns a discriminated union of typed link descriptors
per role — the same shape `use-breadcrumbs.ts` already uses, so no URL is built from a string and no
`any` appears — derived from the session role through `entities/session/model/role-guards`.
`widgets/app-shell/ui/primary-nav.tsx` renders it in the shell; `pages/dashboard` renders the same
descriptors as the landing area's entries, so the header and the landing page cannot drift apart.
`coach` and `player_parent` yield an empty list, which is correct rather than missing: this feature
gives them no dedicated page beyond `/profile` and the context switcher.

D-05 stands unchanged — the shell gains a nav region beside the breadcrumb trail; identity, back
control, and switcher slot are untouched. The breadcrumb `ROUTE_LABELS` map and the `BreadcrumbCrumb`
union gain the two trainer routes, which D-05 predates.

**Rejected**: hand-written `<Link>`s on each page that needs one — that is what produced the defect,
since nothing fails when a page forgets. **Also rejected**: a `nav` field in each route's `staticData`
— it puts presentation labels in the route tree, and the generated `routeTree.gen.ts` is not a file a
reviewer reads for navigation. The orphan-route test (tasks.md T308) is what makes the single list
enforceable: it walks the generated route tree and fails on any authenticated path no role can reach.

---

## Extension (2026-08-26): ShareLink Onboarding, Multi-Trainer & Portal Branding

**Spec basis**: User Stories 6–8, FR-065 – FR-104, SC-015 – SC-025.
**Phase 0**: [research.md](./research.md) Part C, R-21 – R-33.
**Phase 1**: [data-model.md](./data-model.md) §15–§24,
[contracts/openapi.yaml](./contracts/openapi.yaml) v1.1.0,
[contracts/frontend-contracts.md](./contracts/frontend-contracts.md) §8–§14,
[quickstart.md](./quickstart.md) US6–US8.

### Summary of the extension

Players stop being hand-created. Every trainer holds one standing invitation link they can print or
post; anyone who opens it sees a branded join page and registers into that trainer's roster in a
single transaction. A player who opens a second trainer's link joins it with the same account, and
from then on lives in one trainer context at a time — a boundary the server resolves and enforces
rather than the client selecting. Trainers put their own logo and colour on the portal their players
and coaches see.

Four decisions carry most of the weight, and each is argued in `research.md`:

- **The ShareLink code is stored in clear** (R-21), alone among this system's tokens. FR-069 requires
  the trainer to read it back at any time, which a hash forbids, and the link is meant to be
  published. 128 bits of entropy plus a per-origin throttle is what keeps FR-066 true.
- **Context is resolved server-side from the player's own row** (R-24, R-25). No endpoint takes a
  `trainer_id`. Epics 02–08 will add dozens of context-scoped endpoints; if context arrived as a
  parameter, each would have to remember to validate it, and one omission is a cross-tenant read.
- **Context-scoped query keys are namespaced `['ctx', trainerId, …]`** (R-26). Fixing this convention
  now, while the namespace holds one entry, is what stops User Story 7's isolation rule from being
  retrofitted across eight epics later.
- **SVG logos are handled without a new dependency** (R-27): refuse a DOCTYPE, screen with the
  standard library, serve inertly, render only through `<img>`. The constitution forbids adding a
  sanitizer library, and this is the layered answer that does not need one.

### Technical Context — what changed

**Dependencies**: **none added.** This is worth stating rather than assuming: the two places that
would normally pull one in are SVG sanitization (R-27, answered with `xml.etree` plus a DOCTYPE
refusal and inert serving) and colour-contrast maths (R-29, a dozen lines of arithmetic in
`shared/lib/brand-palette.ts`). Pillow already handles the raster logo path, and `secrets` already
generates the codes. The locked stack is untouched, so no constitution amendment is required.

**Storage**: three new tables — `share_links`, `trainer_player_associations`,
`link_lookup_attempts` — and eight new columns on two existing tables. Portal logos join profile
photos behind the same storage port, with one difference: logos are served **unauthenticated**,
because FR-073 puts branding on a page reached before anyone has an account.

**Performance goals**: joining an additional trainer within 5 s (SC-016); a context switch within
2 s (SC-018); a revoked link dead within 1 minute (SC-020, immediate by construction — the check is
a column read in the same predicate); a branding change visible within 1 minute without signing out
(SC-022, achieved by the session query's refetch rather than by any push mechanism).

**Constraints**: unchanged, plus one new class of test that must not be treated as optional — the
cross-trainer isolation sweep (SC-025). A permission matrix proves roles cannot reach each other's
actions; it does not prove that one trainer's data never appears in another's response body. Those
are different failures and need different tests.

**Scale/Scope**: 33 API operations (19 + 14); 12 database tables (9 + 3); nine frontend routes plus
three layout routes; 104 functional requirements.

### Constitution Check — re-evaluated for the extension

Evaluated against `.specify/memory/constitution.md` v1.1.0.

| Principle | Verdict | How the extension satisfies it |
|---|:---:|---|
| I. Spec-Driven Development | PASS | `spec.md` was extended and validated before this plan; these artifacts contain no functional code. Notably, the coach half of FR-101 is **not** implemented ahead of US-01.08 — see R-33 and the recorded judgement below. |
| II. End-to-End Type Safety | PASS | `ShareLinkKind`, `AssociationStatus`, and `Gender` are closed enums, not free text (data-model §15), so the join page's four-way `viewer.state` branch is exhaustive at compile time. New request and response models are Pydantic V2; their Zod mirrors are tabulated in `frontend-contracts.md` §10. |
| III. Layered Backend Architecture | PASS | Four new services — `join_service`, `share_link_service`, `trainer_context_service`, `branding_service` — over three new repositories. Trainer context is resolved in a `Depends` (`get_trainer_context`), the same shape R-14 gives the role gate, so no router and no repository decides it. |
| IV. Feature-Sliced Frontend | PASS | New slices assigned in `frontend-contracts.md` §8–§13. The judgement call is §11: the active trainer context **looks** like UI state and is not — it is server state owned by TanStack Query, because the server corrects it (FR-089) and it persists across devices (FR-086). The Zustand store gains exactly one field, and it is whether a dropdown is open. |
| V. Async-First & Contained Failures | PASS | No new raw SQL: revision 7's backfill is written with Core constructs against `op.get_bind()`, so the two documented exceptions stay at two. FR-070's single refusal message for five distinct causes is contained-failure behaviour applied to an unauthenticated surface. |
| VI. Null-Not-Empty Data Contract | PASS | Every new nullable field is `str \| None` with `min_length=1`; `PortalBrandingUpdate` distinguishes an omitted key from an explicit `null` through `model_dump(exclude_unset=True)`, which is how FR-100's reset and FR-104's "absent means default" coexist. The join form routes through the single `normalizeEmptyToNull` helper D-01 established — no second normalizer. |
| Stack constraints | PASS | **Zero dependencies added**, as above. Branding colours reach components as CSS custom properties overriding `DESIGN_TOKENS.md` defaults, so no component holds a hex literal and the design-token rule survives runtime theming. Three new Alembic revisions. |
| Workflow & quality gates | PASS | `quickstart.md` gains the isolation sweep, the throttle trial, the contrast sweep, the SVG fixture set, and two greps; the existing permission matrix gains every new route. |

**Gate result: PASS.** No new violations, no new exceptions, no amendment needed.

### Project Structure — files the extension adds

```text
backend/src/app/
├── models/
│   ├── share_link.py                 # share_links
│   └── association.py                # trainer_player_associations, link_lookup_attempts
├── schemas/
│   ├── join.py                       # preview, registration, result
│   ├── share_link.py
│   ├── trainer_context.py
│   └── branding.py
├── repositories/
│   ├── share_link_repository.py
│   ├── association_repository.py
│   └── link_lookup_attempt_repository.py
├── services/
│   ├── join_service.py               # the one transaction of R-23
│   ├── share_link_service.py         # issue, read, regenerate, the five-part usability predicate
│   ├── trainer_context_service.py    # resolve-and-repair (R-24), switch, list
│   ├── branding_service.py           # resolve_for_viewer, logo lifecycle
│   └── svg_screening.py              # R-27 layer 1 — stdlib only
├── core/deps.py                      # + get_trainer_context
└── api/v1/
    ├── join_router.py                # public
    ├── trainer_router.py             # roster
    ├── me_router.py                  # + share-link, trainers, trainer-context, branding
    └── media_router.py               # + public /media/branding/{key}

backend/migrations/versions/
├── 0005_create_share_links_and_associations.py
├── 0006_extend_player_details_and_branding.py
└── 0007_backfill_trainer_share_links.py        # Core constructs, idempotent

frontend/src/
├── routes/
│   ├── join.$code.tsx                # public — beside login.tsx, NOT under _authed
│   └── _authed/trainer/{portal,players}.tsx  (+ trainer.tsx layout route)
├── pages/{join,trainer-portal,trainer-players}/
├── widgets/
│   ├── branding-provider/            # session branding → CSS custom properties
│   ├── trainer-context-switcher/
│   └── app-shell/                    # + switcher slot
├── features/
│   ├── join/{register,accept}/
│   └── trainer/{share-link,branding}/
├── entities/
│   ├── join/                         # preview query
│   └── trainer-context/              # ctxKeys namespace, switch mutation, roster query
└── shared/lib/brand-palette.ts       # pure: primary hex → readable palette (R-29)
```

`routes/join.$code.tsx` sits at the top level deliberately: `_authed` redirects to `/login` when
there is no session, which is exactly the visitor the join page exists to serve.

### Implementation Sequence — phases 7 to 10

| Phase | Delivers | Backend | Frontend | Proves |
|---|---|---|---|---|
| 7 | **US6** — joining through a link | Revisions 5–7; share-link issue/read/regenerate; the join transaction; the throttle; the roster | Public join page with its four-way branch; trainer portal page's link half; roster table | SC-015, SC-019, SC-020, SC-021 |
| 8 | **US7** — multi-trainer and context | `accept`; context resolve-and-repair; `PUT /me/trainer-context`; the `ctx` dependency; isolation sweep | Context switcher; `ctx` key namespace; switch-and-drop-cache | SC-016, SC-017, SC-018, SC-025 |
| 9 | **US8** — portal branding | Branding read/update/reset; logo upload with raster fitting and SVG screening; public logo delivery | Branding controls with preview; `brand-palette.ts`; branding provider on both mount points | SC-022, SC-023, SC-024 |
| 10 | Hardening | Permission matrix extended to every new route; throttle trial; backfill idempotence | Contrast sweep; empty-state coverage for a player with no trainer | Full suite green |

Phase 7 carries all three migrations for the same reason phase 1 carried four: they are one schema
change, and splitting them across phases would create revisions that exist only to be superseded.

The roster (`GET /trainer/players`) lands in phase 7 rather than phase 8, even though it is a
trainer-scoped view, because US6's Independent Test is "the trainer sees the new player on their
roster" — without it, phase 7 cannot be demonstrated.

### Complexity Tracking — extension

**No new deviations from the constitution.** The two raw-SQL exceptions stand at two; revision 7's
backfill is Core constructs, and no new dependency was added. What follows are three judgements a
reviewer should see stated rather than discover, in the same spirit as the erasure judgement above.

| Judgement | What it is | Why, and what would change it |
|---|---|---|
| **ShareLink codes are stored in clear** | Every other secret here — session tokens, setup invitations — is stored as a SHA-256. This one is not. | FR-069 requires the trainer to read the link back at any time, which a hash makes impossible, and the link is designed to be published on a flyer. What it grants is one thing the trainer is already offering publicly. If the coach single-use variety (US-01.08) is added, **it should be hashed** — it is addressed to one person and shown once, so the reasoning inverts. R-21. |
| **`/media/branding/{key}` is unauthenticated** | Profile photos require a session; logos do not. | FR-073 puts a trainer's branding on the join page, which is reached before an account exists. The exposure is a logo the trainer is printing on flyers, behind an opaque key. If branding ever carried something non-public, this endpoint is where that assumption breaks. |
| **The coach half of FR-101 is not implemented** | A coach sees the platform default, not their trainer's branding. | Which trainer a coach works for is US-01.08, out of scope, so `coach_details` has no employer column and nothing could populate one. `branding_service.resolve_for_viewer` carries the branch and a `TODO(US-01.08)`; adding the column speculatively would be building US-01.08 ahead of its spec, which Principle I forbids. **This is a known gap between FR-101 as written and what ships.** R-33. |

### Open dependency to raise before implementation

FR-101 cannot be fully satisfied until US-01.08 (trainer invites coach) establishes the coach-to-
trainer relationship. Everything else in User Story 8 ships complete: trainers set their branding,
players see it in the right context, the join page is branded, and the platform default holds
everywhere else. The coach audience is one function branch away and is marked as such. If the coach
half is required in this slice, the coach-to-trainer link has to come into scope with it — that is a
spec decision, not a plan one.

---

## Extension (2026-08-27): Family Accounts, Child Sign-In & the Approval Workflow

**Spec basis**: User Stories 9–13, FR-106 – FR-159, SC-027 – SC-041.
**Phase 0**: [research.md](./research.md) Part D, R-34 – R-51.
**Phase 1**: [data-model.md](./data-model.md) §25–§35,
[contracts/openapi.yaml](./contracts/openapi.yaml) v1.2.0,
[contracts/frontend-contracts.md](./contracts/frontend-contracts.md) §15–§21,
[quickstart.md](./quickstart.md) US9–US13.

### Summary of the extension

An account stops being one player and becomes a family. A parent adds children, decides which
trainers each child trains with, and may give a child their own way in — a sign-in that can look but
not spend, not commit, and not reach a sibling. Anything a child asks for that costs money or changes
who they train with stops and waits at **Pending Parent Approval** until the parent approves, denies,
asks a question, or lets the 48-hour clock run out.

**The structural change comes first, and it is the bulk of the work.** `player_details.user_id` is a
primary key that asserts one player per account, and FR-106 removes that assertion. So
`player_profiles` replaces it with a surrogate key, `trainer_player_associations` is re-pointed at the
profile, and the active context moves to a table keyed by the *viewer* rather than the player.
[data-model.md](./data-model.md) §35 lists the ten backend call sites, four frontend modules, and
thirteen test files that encode the old shape — that list, not the four table changes, is the honest
size of this slice, and it is why Phase 11 exists.

Five decisions carry most of the weight, each argued in `research.md`:

- **The migration is three revisions, and its downgrade refuses to lose data** (R-35). Structure,
  then data, then constraints — because SQLite rebuilds a table for every `ALTER COLUMN` and
  `DROP CONSTRAINT`, and a rebuild racing a backfill leaves a schema neither `upgrade` nor
  `downgrade` describes. Revision 9's downgrade raises rather than silently discarding a parent's
  second and third child.
- **The approval workflow is one generic mechanism with an executor registry** (R-39, R-42). Three
  kinds, one table, typed subject columns rather than a JSON payload. Approval performs the action in
  the same transaction, so a failure leaves the request live instead of approved-but-undone.
- **Two guarantees are pushed into the schema rather than the service** (R-40, R-41). A partial unique
  index makes "one live request per child and subject" true by construction; a single conditional
  `UPDATE` whose row count *is* the decision makes "resolved exactly once" true without a lock, and
  folds the expiry race and the non-Active-parent rule into the same predicate.
- **Expiry needs two mechanisms, not one** (R-43). The predicate makes a lapsed request unapprovable
  immediately; the existing `prune` subcommand materializes the status and sends the two
  notifications FR-155 requires. Neither substitutes for the other, and the second is an operational
  obligation this plan records rather than assumes.
- **Sibling isolation rides the context dependency** (R-48). R-25 kept `trainer_id` out of every
  endpoint so that a forgotten check could not become a cross-tenant read; FR-117 adds a second axis
  with a nastier failure mode, because a sibling is on the *same account* and passes any ownership
  check that stops at the account.

### Technical Context — what changed

**Dependencies**: **none added**, for the third slice running. The two places that might have pulled
one in are scheduling (R-43, answered by the `prune` subcommand that already exists) and
money-handling (R-39, answered by an integer of minor units, since this slice stores amounts and
executes none). The locked stack is untouched, so no constitution amendment is required.

**Storage**: three new tables — `player_profiles`, `active_training_contexts`, `approval_requests` —
one table **dropped** (`player_details`), and one existing table's foreign key re-pointed
(`trainer_player_associations`). Two of the new indexes are **partial**, which is the first use of
that feature in this schema and is what moves two correctness rules out of service code (R-40, R-41).

**Performance goals**: a child added and placed with a trainer in under 2 minutes (SC-027); a parent
notified within 1 minute of a request and able to decide in under 1 more (SC-032); an approved join
on the trainer's roster within 5 seconds (SC-033); child sessions stopped within 1 minute of the
parent's deactivation (SC-041, immediate by construction — the same in-transaction revocation
data-model §5 already uses). The family list is deliberately **not paged**: a family is small, and
FR-124 asks for the whole list at once.

**Constraints**: unchanged, plus two new classes of test that must not be treated as optional. The
**sibling isolation sweep** (SC-028, SC-040) is not covered by the permission matrix or by the
existing cross-trainer sweep — "a child cannot reach an action" and "a sibling's data never appears in
a response body" are different failures, and so are "another trainer's data" and "another profile on
the same account". The **migration verification** (data-model §33) is the other: revision 9 re-points
every association in the system, and no downstream test is meaningful if it silently dropped rows.

**Scale/Scope**: 51 API operations (33, less the 2 replaced context routes, plus 20 new); 16 database
tables (14 + 3 new − `player_details`); thirteen frontend routes plus four layout routes; 159
functional requirements.

### Constitution Check — re-evaluated for the extension

Evaluated against `.specify/memory/constitution.md` v1.1.0.

| Principle | Verdict | How the extension satisfies it |
|---|:---:|---|
| I. Spec-Driven Development | PASS | `spec.md` was extended and validated before these artifacts, which contain no functional code. The principle is most visible where it *costs* something: the USD and token approval kinds are specified but deliberately **not executable**, because their execution is Epic-05's spec, and a stub that "succeeded" would be code ahead of an approved spec (R-46). |
| II. End-to-End Type Safety | PASS | Three new closed enums (`PlayerProfileKind`, `ApprovalRequestKind`, `ApprovalRequestStatus`), so the parent's queue and the switcher's grouping branch exhaustively at compile time. The approval subject is **typed nullable columns with check constraints**, explicitly not a JSON blob — the untyped-dict shape Principle II exists to exclude (R-39). New Pydantic V2 models; Zod mirrors tabulated in `frontend-contracts.md` §17. |
| III. Layered Backend Architecture | PASS | Four new services — `family_service`, `child_signin_service`, `approval_service`, `training_context_service` (renamed from `trainer_context_service`) — over two new repositories, plus `approval_executors.py` holding the registry and no queries. The context pair is resolved in a `Depends` (`get_training_context`), the same shape R-14 gives the role gate, so neither a router nor a repository decides isolation (R-48). |
| IV. Feature-Sliced Frontend | PASS | New slices assigned in `frontend-contracts.md` §15–§17. **The Zustand store gains nothing**, which took deciding: the expiry countdown is derived at render from `expires_at` rather than ticked in a store, and the duplicate-child dialog reads the 409 from mutation error state rather than copying it (§18). Server state stays owned by TanStack Query throughout. |
| V. Async-First & Contained Failures | PASS | No new raw SQL: revision 9's data migration is Core constructs against `op.get_bind()`, exactly as revision 7 was, so **the two documented exceptions stay at two** and the CI grep on `.execute("` still passes. R-41's conditional update is a Core `update()` with a `where` clause. FR-090's and FR-132's single 404 for several distinct causes is contained-failure behaviour applied to a new surface — a sibling must not be confirmed to exist. |
| VI. Null-Not-Empty Data Contract | PASS | Every new nullable string is `str \| None` with `min_length=1`; `PlayerProfileUpdate` and `PortalBrandingUpdate` share the same `model_dump(exclude_unset=True)` semantics, so an omitted key differs from an explicit `null`. The two approval note fields are the sharpest case and are called out in `frontend-contracts.md` §17: a parent who opens the note box, types nothing, and approves must send `null`, not `''`. All new forms route through the existing single `normalizeEmptyToNull` helper — no second normalizer. |
| Stack constraints | PASS | **Zero dependencies added.** Three new Alembic revisions (data-model §33). No component holds a colour literal; nothing in this slice touches theming. |
| Workflow & quality gates | PASS | `quickstart.md` gains the sibling isolation sweep, the child permission sweep, three concurrency races, the migration verification, the family erasure check, and one grep; the permission matrix gains every new route. |

**Gate result: PASS.** No new violations, no new exceptions, no amendment needed.

**One housekeeping correction, not a gate failure**: the constitution's standing
`TODO(NULL_NORMALIZATION_HELPER)` says the frontend "has no shared empty-string-to-null helper yet"
and that existing forms must be migrated onto one. That TODO is **stale** —
`frontend/src/shared/lib/normalize-payload.ts` exists, is the single normalizer, and is covered by
`tests/shared/normalize-payload.test.ts`; D-01 delivered it and the bug-fix slice's Constitution Check
already recorded it as discharged. The constitution's own text was never updated. Correcting it is a
PATCH-level amendment to `.specify/memory/constitution.md` and is listed as a task rather than done
here, because this document is not the place to edit the constitution.

### Project Structure — files the extension adds

```text
backend/src/app/
├── models/
│   ├── player_profile.py             # player_profiles, active_training_contexts
│   ├── approval.py                   # approval_requests
│   └── role_details.py               # − PlayerDetail (removed with revision 10)
├── schemas/
│   ├── player_profile.py             # profile read/create/update, duplicate-match error
│   ├── child_signin.py
│   ├── approval.py                   # request read, decision, info exchange, page
│   └── training_context.py           # replaces trainer_context.py
├── repositories/
│   ├── player_profile_repository.py
│   └── approval_repository.py        # incl. the conditional-resolve update (R-41)
├── services/
│   ├── family_service.py             # profiles, their trainers, the duplicate check (R-45)
│   ├── child_signin_service.py       # grant, revoke, and the derived "is a child" (R-38)
│   ├── approval_service.py           # create, resolve, expire
│   ├── approval_executors.py         # the registry; one implementation (R-42, R-46)
│   ├── training_context_service.py   # renamed; resolve-and-repair over the pair (R-36)
│   └── maintenance_service.py        # + expire_lapsed_approval_requests (R-43)
├── core/deps.py                      # get_training_context replaces get_trainer_context
├── cli.py                            # prune: + approval expiry, widened help text
└── api/v1/
    ├── family_router.py              # /me/players…
    ├── approvals_router.py           # /me/approvals…, /me/requests…
    ├── me_router.py                  # /me/contexts, /me/context replace the two trainer routes
    ├── join_router.py                # + family-member selection, + child blocking
    └── trainer_router.py             # roster reshaped to profiles

backend/migrations/versions/
├── 0008_create_player_profiles_and_approvals.py
├── 0009_migrate_players_to_profiles.py            # Core constructs; downgrade refuses to lose data
└── 0010_finalize_profile_associations.py          # batch_alter_table; drops player_details

frontend/src/
├── routes/_authed/
│   ├── family.tsx  family/index.tsx  family/$profileId.tsx
│   ├── approvals.tsx                 # parent's decision queue
│   └── requests.tsx                  # a child's own requests
├── pages/{family,family-player,approvals,requests}/
├── widgets/
│   ├── trainer-context-switcher/     # regrouped by profile (frontend-contracts §19)
│   ├── family-roster-list/
│   └── app-shell/model/use-nav-items.ts   # player_parent stops returning []
├── features/
│   ├── family/{add-child,edit-player,add-trainer,remove-trainer,grant-sign-in}/
│   ├── approvals/decide/
│   └── join/accept/                  # + the family-member picker
└── entities/
    ├── player-profile/               # familyKeys, profile queries
    ├── approval/                     # approvalKeys, queue and raised queries
    └── trainer-context/              # ctxKeys widened to (profileId, trainerId)
```

`routes/_authed/requests.tsx` and `routes/_authed/approvals.tsx` are separate routes rather than one
filtered view because they serve different callers: a child sees what they asked for, a parent sees
what they must decide, and merging them would put a role branch inside a page instead of in the
navigation descriptor list D-07 established.

### Implementation Sequence — phases 11 to 15

| Phase | Delivers | Backend | Frontend | Proves |
|---|---|---|---|---|
| 11 | **Foundation** — the new shape, no new capability | Revisions 8–10; `player_profiles`, `active_training_contexts`, `approval_requests`; the §35 repository and service rework; `get_training_context` | `ctxKeys` widened; `/me/contexts` wired; switcher regrouped; types regenerated | Revision 9 verified; **the entire existing suite green on the new shape** |
| 12 | **US9 + US10** — family profiles and their trainers | `/me/players` CRUD, photo, add and remove trainer, the duplicate 409 | `/family` and `/family/$profileId` | SC-027, SC-028 |
| 13 | **US11** — child sign-in and the blocked link | Grant and revoke sign-in; the child permission gate; join blocking that raises a request | Child views, nav entries, empty states | SC-029, SC-030 |
| 14 | **US12** — the approval workflow | `approval_service`, the executor registry, the conditional resolve, the expiry sweep, notifications | `/approvals`, `/requests`, the pending count | SC-031 – SC-039, SC-041 |
| 15 | **US13 + hardening** | Family-member selection on `accept` | The picker on the join page | SC-019 re-checked, full suite green |

**Phase 11 is the one phase in this whole plan that demonstrates nothing new, and that is deliberate
rather than an oversight.** Every other phase in this document maps to a story's Independent Test.
Phase 11 maps to none: it re-points a foreign key that ten backend call sites and four frontend
modules read. Splitting it across Phases 12–14 was considered and rejected — each story would then
carry part of one migration, the schema would sit half-migrated between phases, and the association
table would have to answer to both `player_user_id` and `player_profile_id` for three phases. Its
proof is therefore regression rather than demonstration: **the existing suite, unchanged in intent,
passing against the new shape.** A reviewer should expect Phase 11 to change many files and add no
user-visible behaviour, and should treat any *new* capability appearing in it as scope leaking out of
Phase 12.

Phases 12 and 13 both precede the approval workflow because a request needs a child, a trainer, and a
sign-in before it has a subject or an author. Phase 14 then adds no schema — `approval_requests` was
created in Phase 11 alongside the rest of the migration, for the same reason Phase 1 carried four
revisions and Phase 7 carried three: they are one schema change, and splitting them creates revisions
that exist only to be superseded.

### Complexity Tracking — extension

**No new deviations from the constitution.** The two raw-SQL exceptions stand at two, no dependency
was added, and no amendment is needed. What follows are judgements and known gaps a reviewer should
see stated rather than discover — the same practice as the erasure judgement above and the three
recorded for the 2026-08-26 slice.

| Judgement | What it is | Why, and what would change it |
|---|---|---|
| **This extension is not additive** | Every earlier slice could say "no existing column changes type or nullability". This one drops a table, re-points a foreign key, and swaps a unique constraint. | FR-106 removes the assertion that `player_details.user_id` — a primary key — encodes. There is no additive way to hold "one account, several players, each with their own trainers" in a table keyed by account (R-34). The blast radius is enumerated in data-model §35 rather than left for implementation to find. |
| **Revision 9's downgrade raises instead of reversing** | `alembic downgrade` fails for any account holding more than one profile. | A clean reversal is impossible in principle: three children do not fit in a table keyed by account. The alternatives are refusing loudly or discarding data silently, and a migration that quietly loses two of a family's three children is the worse failure. Asserted by a test (data-model §33). |
| **A child's name is stored twice** | `player_profiles` holds it, and so does the `user_profiles` row every account is required to have. | §3 makes `user_profiles` mandatory with non-null names, and a child *without* a sign-in has no `users` row, so the profile must hold the name regardless. Contained by making the profile authoritative, giving the copy exactly one writer, and having nothing read it (data-model §26.1). Relaxing `user_profiles.first_name` to nullable would weaken an invariant all four roles rely on, for one case. |
| **The financial approval kinds ship unexecutable** | `usd_payment` and `token_spend` exist in the enum, the columns, and the rules; approving either returns 422. | FR-142 requires the rules and data now and puts execution in Epic-05, and its last clause forbids marking such a request approved before the act can be performed. A stub that succeeded would be the first test asserting money moved when it did not (R-46). **This is a known gap between FR-142 as written and what ships**, closed by Epic-05 registering two executors. |
| **Expiry notification is an operational dependency** | Requests become unapprovable on time by construction, but the "your request expired" email waits for `python -m app.cli prune`. | The locked stack has no scheduler and the application registers no background task; adding either would be a dependency or a lifespan hook for one job that `cron` already schedules (R-43). The obligation is recorded in `quickstart.md` §Quality gates — family accounts, because no test can catch an unscheduled cron job. |
| **1.2.0 breaks the contract on purpose** | `PlayerParentDetail` loses fields, the roster changes shape, and two `/me` operations are replaced rather than deprecated. | The only consumer is this repository's own frontend, shipping in the same commit, and the contract test fails the build on divergence. A parallel v1 shape would mean two serializers kept in step for no external caller; `/api/v2` would leave a permanent scar for a migration that costs nothing today (R-49). |
| **A child's `gender` survives erasure; their `date_of_birth` does not** | Matching §20's treatment of the account holder. | For a one-child family the surviving classification is weakly identifying alongside a trainer's roster. Clearing it costs Epic-02 its age-and-gender grouping over historical events, which FR-047 protects. Same caveat, same one-line fallback as §10's `business_name` judgement — and the spec already flags this family of questions for legal review. |

**Still open from the previous slice, unchanged**: the coach half of FR-101 remains unimplemented
until US-01.08 establishes which trainer a coach works for (R-33). This extension neither closes nor
worsens it.

### Open dependencies to raise before implementation

1. **Revision 9 must be verified against production-shaped data before Phase 12 begins.** It re-points
   every trainer association in the system. The plan's verification point is
   `test_migration_backfill.py` (data-model §33), but a database with real families is the only place
   the `player_name` split heuristic — split on the last space; a one-word name becomes the first name
   and the last name becomes `—` — can be judged acceptable. If it is not, the fix is to prompt for
   the split rather than guess, which is a task, not a redesign.

2. **`prune` must be scheduled at deployment.** Not a code dependency and not testable, which is
   exactly why it is listed. Hourly is sufficient; the correctness guarantee does not depend on it,
   only the notification (R-43).

3. **FR-142's financial kinds cannot be closed in this slice.** If the client requires a working
   purchase approval now, Epic-02's events and Epic-05's payments have to come into scope with it —
   that is a spec decision, not a plan one, and the mechanism is built so that decision costs two
   executor registrations rather than a redesign.

4. **The constitution's stale `TODO(NULL_NORMALIZATION_HELPER)` should be corrected** as a PATCH
   amendment. The helper it asks for exists; leaving the TODO in place teaches the next reader that
   Principle VI is unimplemented.
