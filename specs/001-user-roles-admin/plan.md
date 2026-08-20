# Implementation Plan: User Roles, Authorization & Super Admin User Management

**Branch**: `001-user-roles-admin` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)

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

**Scale/Scope**: 10,000 accounts as the directory performance target; four roles; 19 API operations;
9 database tables; 5 frontend routes plus two layout routes; 56 functional requirements.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.0.

| Principle | Requirement | Pre-Phase-0 | Post-Phase-1 | How the design satisfies it |
|---|---|:---:|:---:|---|
| I. Spec-Driven Development | Spec → Plan → Tasks → Code; no code before approval | PASS | PASS | `spec.md` approved; this plan and its artifacts contain no functional code. `tasks.md` comes next; implementation only after. |
| II. End-to-End Type Safety | No `any`; Pydantic V2 everywhere; boundary parity | PASS | PASS | Role detail is a discriminated union, not a JSON blob (R-15), so narrowing uses type guards. Zod-to-Pydantic parity is tabulated in `contracts/frontend-contracts.md` §3. `unknown` plus `isApiError` is the single narrowing point for errors. |
| III. Layered Backend Architecture | Router → service → repository; `Depends`; no global state | PASS | PASS | Directory tree below assigns one layer per package. Role gate is a dependency; state-dependent rules are in services; all queries in repositories (R-14). Settings and sessions are injected, never module-level. |
| IV. Feature-Sliced Frontend | FSD layers, one-way imports, `shared/ui`, `shared/api`, Query for server state, Zustand for UI only | PASS | PASS | Layer mapping in R-17; state ownership fixed in `contracts/frontend-contracts.md` §4. The Zustand store holds three UI fields and `pendingAction` deliberately stores a `userId`, not an account object. |
| V. Async-First & Contained Failures | Async I/O, `AsyncSession`, no raw SQL, service-layer error translation | PASS | **PASS with 2 documented exceptions** | Every I/O path is `async`. Domain errors raised in services map to `HTTPException` in routers through one handler; the single `Error` envelope in the contract carries no internal detail (FR-056). The two raw-SQL exceptions are recorded in Complexity Tracking. |
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
├── research.md                      # Phase 0 — 20 decisions, both clarifications resolved
├── data-model.md                    # Phase 1 — 9 tables, transitions, erasure mapping
├── quickstart.md                    # Phase 1 — setup and story-by-story validation
├── contracts/
│   ├── openapi.yaml                 # Phase 1 — 19 operations, 24 schemas
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
