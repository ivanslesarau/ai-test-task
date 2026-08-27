---

description: "Task list for feature 001-user-roles-admin"
---

# Tasks: User Roles, Authorization & Super Admin User Management

**Input**: Design documents from `/specs/001-user-roles-admin/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Test tasks ARE included. Not by default — the constitution's Development Workflow section
makes passing tests a merge gate, SC-002 requires a permission matrix proven across every role and
route, and `research.md` R-20 fixes the tooling. Tests are therefore a stated requirement of this
feature, not an optional extra.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and
demonstrated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1–US5)
- Exact file paths are given in every task

## Path Conventions

Web application, two packages at repository root (plan.md §Project Structure):

- Backend: `backend/src/app/`, tests in `backend/tests/`
- Frontend: `frontend/src/`, tests in `frontend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Both applications start, tooling enforces the constitution's rules from the first commit.

- [X] T001 Create the two-package skeleton — `backend/src/app/`, `backend/tests/{unit,integration,contract}/`, `backend/migrations/`, `frontend/src/`, `frontend/tests/` — matching the tree in plan.md §Project Structure
- [X] T002 Initialize the backend project in `backend/pyproject.toml` with FastAPI, SQLAlchemy 2.0, `aiosqlite`, Pydantic V2, `pydantic-settings`, Alembic, `pwdlib[argon2]`, Pillow, `aiosmtplib`, and dev extras pytest, `pytest-asyncio`, `httpx`, ruff, mypy
- [X] T003 [P] Configure ruff and strict mypy in `backend/pyproject.toml` — `disallow_untyped_defs`, `warn_return_any`, `strict_equality` — so Principle II is enforced by the type checker rather than by review
- [X] T004 [P] Configure pytest in `backend/pyproject.toml` with `asyncio_mode = "auto"` and the `unit`/`integration`/`contract` test paths
- [X] T005 [P] Initialize the frontend project with Vite, React 19, and TypeScript in `frontend/package.json` and `frontend/vite.config.ts`
- [X] T006 [P] Enable TypeScript strict mode plus `noUncheckedIndexedAccess` and the `@/*` path alias in `frontend/tsconfig.json` and `frontend/tsconfig.app.json`
- [X] T007 Install and configure Tailwind CSS v4 through `@tailwindcss/vite` in `frontend/vite.config.ts`, with the CSS-first config in `frontend/src/app/styles/globals.css` (research.md R-18)
- [X] T008 Initialize shadcn/ui with `frontend/components.json` aliased so generated components land in `frontend/src/shared/ui/` — the default `components/ui` path would violate Principle IV on every `add` command
- [X] T009 [P] Add ESLint to `frontend/eslint.config.js` with `@typescript-eslint/no-explicit-any` set to error and an import-boundaries rule enforcing the FSD layer order app → pages → widgets → features → entities → shared
- [X] T010 [P] Configure Vitest, React Testing Library, and MSW in `frontend/vitest.config.ts` and `frontend/tests/setup.ts`
- [X] T011 [P] Initialize Alembic with the async template in `backend/migrations/env.py`, importing every model module so autogenerate does not produce empty revisions
- [X] T012 [P] Write `backend/.env.example` listing every key in quickstart.md §2 with no secret values
- [X] T013 [P] Write `frontend/.env.example` with `VITE_API_BASE_URL`, and add the `/api` dev proxy to `frontend/vite.config.ts` so the session cookie stays first-party
- [X] T014 [P] Transcribe the typography, colour, and spacing tokens from `Task/designs/DESIGN_TOKENS.md` into CSS custom properties and Tailwind theme values in `frontend/src/app/styles/globals.css`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The complete data model, configuration, error handling, and both application shells.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

The whole schema lands here rather than growing per story: the four Alembic revisions are one
coherent schema, and splitting them across stories would create migrations that exist only to be
superseded (plan.md §Implementation Sequence).

### Backend configuration and database

- [X] T015 Implement the `pydantic-settings` settings class in `backend/src/app/core/config.py` covering every key in `.env.example`, failing startup on any missing value rather than falling back to a default
- [X] T016 Create the async engine in `backend/src/app/db/engine.py` with a connect-event emitting `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, and `busy_timeout` — the first documented raw-SQL exception (plan.md §Complexity Tracking); add the comment explaining why no ORM construct exists for it
- [X] T017 Implement the per-request `AsyncSession` provider in `backend/src/app/db/session.py`, committing on success and rolling back on exception, exposed via `Depends`
- [X] T018 [P] Define `DeclarativeBase` with the UTC timestamp and UUID-text column conventions in `backend/src/app/db/base.py`

### Models

- [X] T019 [P] Define the `UserRole` and `AccountStatus` string enums plus their permitted-transition map in `backend/src/app/models/enums.py` per data-model.md §1
- [X] T020 [P] Define the `users` and `user_profiles` models in `backend/src/app/models/user.py` — nullable `password_hash`, `version` counter, unique lowercased email, and the `(status, role)` and `created_at` indexes
- [X] T021 [P] Define `trainer_organizations`, `coach_details`, `player_details`, and `parent_contacts` in `backend/src/app/models/role_details.py` per data-model.md §4
- [X] T022 [P] Define `sessions`, `credential_setup_invitations`, and `sign_in_attempts` in `backend/src/app/models/auth.py`, with composite indexes on `(email, attempted_at)` and `(client_ip, attempted_at)`
- [X] T023 [P] Define `audit_entries` and `erasure_records` in `backend/src/app/models/audit.py` per data-model.md §8 and §9

### Migrations

- [X] T024 Write Alembic revision 1 `create_users_and_profiles` in `backend/migrations/versions/` with the enum check constraints and indexes
- [X] T025 Write Alembic revision 2 `create_role_detail_tables` in `backend/migrations/versions/`
- [X] T026 Write Alembic revision 3 `create_auth_tables` in `backend/migrations/versions/`
- [X] T027 Write Alembic revision 4 `create_audit_and_erasure` in `backend/migrations/versions/`, including the `CREATE TRIGGER` statements that raise on `UPDATE` and `DELETE` against `audit_entries` — the second documented raw-SQL exception

### Error handling and application shell

- [X] T028 Define the domain error hierarchy in `backend/src/app/core/errors.py` — `NotFound`, `PermissionDenied`, `Conflict`, `StaleVersion`, `ValidationFailure`, `RateLimited`, `InvalidCredentials`, `AccountNotActive`, `InvitationNotUsable` — with no HTTP or SQLAlchemy imports, so services stay framework-free
- [X] T029 Define the `Error`, `ValidationError`, and generic page-wrapper Pydantic models in `backend/src/app/schemas/common.py`, matching the envelope in `contracts/openapi.yaml`
- [X] T030 Register the exception handlers in `backend/src/app/main.py` mapping each domain error to its status code and envelope, with a catch-all that logs the full detail server-side and returns a generic body — FR-056 and SC-012 depend on this being the only path out
- [X] T031 Create the app factory in `backend/src/app/main.py` wiring settings, CORS for the dev origin, and the four v1 routers
- [X] T032 [P] Create the append-only audit repository in `backend/src/app/repositories/audit_repository.py` exposing only `add` and `list_for_target` — no update or delete method is to exist (FR-055)

### Frontend shell

- [X] T033 Create the single axios instance in `frontend/src/shared/api/client.ts` with `baseURL` from config and `withCredentials: true`
- [X] T034 Implement `ApiError`, the `isApiError` type guard, and the 422 field-error extractor in `frontend/src/shared/api/errors.ts` — the one place `unknown` is narrowed
- [X] T035 Implement the response interceptor in `frontend/src/shared/api/interceptors.ts` per `contracts/frontend-contracts.md` §5: normalize every failure to `ApiError`, redirect on 401 except when the failing request is the session query itself, and never redirect on 403
- [X] T036 [P] Hand-write the TypeScript types mirroring the `openapi.yaml` schemas in `frontend/src/shared/api/types.ts`, with role detail as a discriminated union — no `any`, no index signatures
- [X] T037 [P] Create the TanStack Query client with default retry and stale-time policy in `frontend/src/app/providers/query-provider.tsx`
- [X] T038 [P] Create the Zustand UI store in `frontend/src/app/store/ui-store.ts` holding only `isSidebarCollapsed`, `theme`, and `pendingAction` — `pendingAction` stores a `userId`, never a fetched account object
- [X] T039 Create the root route and the `_authed` layout route in `frontend/src/routes/__root.tsx` and `frontend/src/routes/_authed.tsx`, plus router registration in `frontend/src/app/main.tsx`
- [X] T040 [P] Add the shadcn/ui primitives this feature needs — button, input, label, select, table, dialog, alert-dialog, badge, avatar, form, toast — into `frontend/src/shared/ui/`

### Test infrastructure

- [X] T041 Create the pytest fixtures in `backend/tests/conftest.py` — a temporary Alembic-migrated SQLite file per session, an `httpx` client over `ASGITransport`, and per-role authenticated client factories
- [X] T042 [P] Create the MSW handlers and render helpers in `frontend/tests/setup.ts` and `frontend/tests/msw-handlers.ts`, returning payloads shaped by `contracts/openapi.yaml`

**Checkpoint**: Both applications start, `alembic upgrade head` creates all 9 tables, and the test harnesses run green with zero tests.

---

## Phase 3: User Story 1 — Role-Separated Sign-In (Priority: P1) 🎯 MVP

**Goal**: Four roles exist, people sign in with email and password, each lands in their role's area, every permission boundary is enforced server-side, and a non-Active account cannot get in.

**Independent Test**: Seed one account per role, sign in as each, confirm each reaches its own landing area and is refused when attempting another role's action — including by direct request, not just through the interface. Confirm a deactivated account cannot sign in.

### Tests for User Story 1

> Write these first and confirm they fail before implementing.

- [X] T043 [P] [US1] Unit-test the password policy — 12-character minimum, breached-list rejection — in `backend/tests/unit/test_password_policy.py`
- [X] T044 [P] [US1] Unit-test the sliding-window rate limiter, including automatic recovery as the window passes, in `backend/tests/unit/test_rate_limit.py`
- [X] T045 [P] [US1] Unit-test the status-transition map, asserting every disallowed transition raises, in `backend/tests/unit/test_status_transitions.py`
- [X] T046 [P] [US1] Integration-test `/auth/login`, `/auth/logout`, and `/auth/session` in `backend/tests/integration/test_auth.py` — success, wrong password and unknown email returning byte-identical 401 bodies, 403 for a non-Active account, cookie flags `HttpOnly` and `SameSite=Lax`, and session reuse after sign-out
- [X] T047 [P] [US1] Integration-test the **permission matrix** in `backend/tests/integration/test_permission_matrix.py` — every role against every restricted route, asserting 403 and no state change; this is the test SC-002 requires and it grows with each later story
- [X] T048 [P] [US1] Integration-test that sign-in is refused after 10 failures within the window and admitted again after it passes, in `backend/tests/integration/test_signin_rate_limit.py`
- [X] T049 [P] [US1] Component-test the sign-in form's validation and error rendering in `frontend/tests/features/sign-in.test.tsx`
- [X] T050 [P] [US1] Component-test the route guards — unauthenticated redirect to `/login`, and the Super Admin gate refusing a Trainer — in `frontend/tests/routes/guards.test.tsx`

### Implementation for User Story 1

- [X] T051 [P] [US1] Implement Argon2id hashing and verification via `pwdlib`, opaque token generation, and SHA-256 token hashing in `backend/src/app/core/security.py`
- [X] T052 [P] [US1] Add the bundled breached-password list as `backend/src/app/core/breached_passwords.txt` and the in-process membership check plus length rule in `backend/src/app/core/password_policy.py`
- [X] T053 [P] [US1] Implement the session repository in `backend/src/app/repositories/session_repository.py` — create, find by token hash, advance last-seen, revoke one, revoke all for a user
- [X] T054 [P] [US1] Implement the sign-in attempt repository in `backend/src/app/repositories/sign_in_attempt_repository.py` — record an attempt, count recent failures by email and by client address
- [X] T055 [US1] Implement the user repository read paths in `backend/src/app/repositories/user_repository.py` — get by id, get by lowercased email, count active Super Admins — using ORM constructs only
- [X] T056 [US1] Implement `AuthService` in `backend/src/app/services/auth_service.py` — rate-limit check, credential verification, Active-status and usable-password checks, session issue, session validation with sliding expiry, sign-out — raising domain errors, never `HTTPException`
- [X] T057 [US1] Implement the `Depends` providers in `backend/src/app/core/deps.py` — `get_current_user` reading the cookie and rejecting an expired, revoked, or non-Active session, and a `require_roles(*roles)` factory for the role gate
- [X] T058 [US1] Write an audit entry of action `permission_denied` whenever the role gate refuses a request, in `backend/src/app/core/deps.py` (FR-020)
- [X] T059 [US1] Define the auth request and response schemas in `backend/src/app/schemas/auth.py` — `LoginRequest` and `CurrentUser` per `contracts/openapi.yaml`
- [X] T060 [US1] Implement `/auth/login`, `/auth/logout`, and `/auth/session` in `backend/src/app/api/v1/auth_router.py`, setting and clearing the cookie with `Secure` driven by `APP_ENV`
- [X] T061 [US1] Implement the idempotent `bootstrap-superadmin` command in `backend/src/app/cli.py`, reading credentials from the environment, refusing to run if any Super Admin exists, and writing an audit entry
- [X] T062 [P] [US1] Implement the current-session query hook and role predicates in `frontend/src/entities/session/api/use-session.ts` and `frontend/src/entities/session/model/role-guards.ts`
- [X] T063 [P] [US1] Implement the query-key factory in `frontend/src/entities/user/api/query-keys.ts` exactly as specified in `contracts/frontend-contracts.md` §2
- [X] T064 [US1] Implement the sign-in feature — TanStack Form with the `signInSchema` Zod schema and the sign-out mutation — in `frontend/src/features/auth/sign-in/` and `frontend/src/features/auth/sign-out/`
- [X] T065 [US1] Build the login page in `frontend/src/pages/login/` and the `/login` route in `frontend/src/routes/login.tsx` with the typed `redirect` search param
- [X] T066 [US1] Add the `_admin` layout route enforcing the Super Admin gate in `frontend/src/routes/_authed/admin.tsx`, rendering a clear refusal rather than an empty view
- [X] T067 [US1] Build the per-role landing page in `frontend/src/pages/dashboard/` and the `/` route in `frontend/src/routes/_authed/dashboard.tsx`, branching on role through the type-guard predicates

**Checkpoint**: US1 is independently demonstrable — all four roles sign in, land correctly, and are refused across the boundary. The permission matrix and rate-limit tests pass.

---

## Phase 4: User Story 2 — Super Admin Creates a Trainer Account (Priority: P1)

**Goal**: A Super Admin creates an account in any of the four roles from the user directory; the person receives a single-use setup link, sets their own password, and signs in.

**Independent Test**: Sign in as a Super Admin, create a Trainer, follow the emailed link to set a password, sign in as that Trainer. Attempt a duplicate email and confirm the clear rejection.

**Depends on**: US1 (a Super Admin must be able to sign in before they can create anyone).

### Tests for User Story 2

- [X] T068 [P] [US2] Integration-test account creation in `backend/tests/integration/test_create_user.py` — 201 for each of the four roles, `business_name` required for trainer and rejected otherwise, 409 on duplicate email in any status, 422 listing multiple offending fields at once, and no partial account left behind when the transaction fails
- [X] T069 [P] [US2] Integration-test the invitation lifecycle in `backend/tests/integration/test_invitation.py` — consume once, 410 on reuse, 410 when expired, 410 when superseded, 410 when the account was deactivated before setup, and 422 for a password failing policy
- [X] T070 [P] [US2] Integration-test re-invitation in `backend/tests/integration/test_reinvite.py` — supersedes the outstanding link, and is refused for an account that already has a password
- [X] T071 [P] [US2] Integration-test the directory in `backend/tests/integration/test_user_directory.py` — paging, name and email search, role and status filters, sort orders, and `page_size` capped at 100
- [X] T072 [P] [US2] Integration-test that `user_created` and `invitation_issued` audit entries are written with actor, target, and email, in `backend/tests/integration/test_audit_on_create.py`
- [X] T073 [P] [US2] Extend `backend/tests/integration/test_permission_matrix.py` with the create, directory, and reinvite routes for every non-Super-Admin role
- [X] T074 [P] [US2] Component-test the create-user form in `frontend/tests/features/create-user.test.tsx` — conditional `business_name` by role, and 422 field errors mapped onto the right inputs

### Implementation for User Story 2

- [X] T075 [P] [US2] Implement the invitation repository in `backend/src/app/repositories/invitation_repository.py` — create, find usable by token hash, consume, supersede all outstanding for a user
- [X] T076 [P] [US2] Define the `EmailSender` protocol with SMTP and filesystem-sink implementations in `backend/src/app/services/ports/email_sender.py`, selected by `EMAIL_BACKEND`
- [X] T077 [P] [US2] Write the invitation email template, containing the setup link and no password, in `backend/src/app/services/templates/invitation.py`
- [X] T078 [US2] Add the user repository write paths in `backend/src/app/repositories/user_repository.py` — insert account with profile and the matching role detail row, and the paged filtered directory query
- [X] T079 [US2] Define the admin user schemas in `backend/src/app/schemas/admin_user.py` — `CreateUserRequest`, `UserSummary`, `UserDetail`, `CreatedUser`, `UserPage` — including the validator rejecting any email matching the reserved `deleted_*@example.com` pattern
- [X] T080 [US2] Implement `UserAdminService.create_user` in `backend/src/app/services/user_admin_service.py` — one transaction creating account, profile, role detail, audit entry, and invitation, with email send failure reported rather than rolling back the account
- [X] T081 [US2] Implement `UserAdminService.list_users`, `get_user`, and `reinvite` in `backend/src/app/services/user_admin_service.py`, computing `has_password` and `available_actions` from status
- [X] T082 [US2] Implement `AuthService.check_invitation` and `AuthService.setup_password` in `backend/src/app/services/auth_service.py` — validate usability, apply the password policy, set the hash, consume the invitation
- [X] T083 [US2] Implement `GET /auth/setup-password/{token}` and `POST /auth/setup-password` in `backend/src/app/api/v1/auth_router.py`, returning only a masked email hint on the check
- [X] T084 [US2] Implement `POST /admin/users`, `GET /admin/users`, `GET /admin/users/{user_id}`, and `POST /admin/users/{user_id}/reinvite` in `backend/src/app/api/v1/admin_users_router.py` behind the Super Admin role gate
- [X] T085 [US2] Implement `GET /admin/users/{user_id}/audit` in `backend/src/app/api/v1/admin_users_router.py`
- [X] T086 [P] [US2] Implement the directory and detail query hooks plus the `directorySearchSchema` in `frontend/src/entities/user/api/use-users.ts` and `frontend/src/entities/user/model/directory-search.ts`
- [X] T087 [US2] Build the create-user feature in `frontend/src/features/admin/create-user/` — TanStack Form with `createUserSchema`, role selector, conditional business-name field, and the invalidation of `userKeys.all` on success
- [X] T088 [US2] Build the user directory table widget in `frontend/src/widgets/user-directory-table/` — paging, search, role and status filters bound to the typed search params, and role and status badges
- [X] T089 [US2] Build the admin users pages and routes in `frontend/src/pages/admin-users/` with `frontend/src/routes/_authed/admin/users.index.tsx` and `users.$userId.tsx`
- [X] T090 [US2] Build the set-password page in `frontend/src/pages/set-password/` and the public `/set-password` route in `frontend/src/routes/set-password.tsx`, checking link validity before showing the form and offering re-request when expired
- [X] T091 [US2] Build the re-invite action in `frontend/src/features/admin/reinvite-user/`, shown only on rows where `has_password` is false

**Checkpoint**: US1 and US2 both work independently. All four roles can now be created, which makes US3–US5 demonstrable across every role.

---

## Phase 5: User Story 3 — Any User Edits Their Own Profile (Priority: P2)

**Goal**: Every signed-in person edits their own name, phone, photo, and role-specific fields; identity fields stay read-only and are rejected, not ignored, when submitted.

**Independent Test**: Sign in as each of the four roles, change every editable field including the photo, save, sign out and back in, confirm persistence. Confirm read-only fields cannot be changed even by direct request.

**Depends on**: US1 for sessions; US2 for non-Super-Admin accounts to test against.

### Tests for User Story 3

- [X] T092 [P] [US3] Unit-test the per-role editable-field rules in `backend/tests/unit/test_editable_fields.py`, asserting a Coach cannot write `jersey_number` and no role can write `skill_level`
- [X] T093 [P] [US3] Integration-test `/me/profile` for all four roles in `backend/tests/integration/test_own_profile.py` — read shape, `editable_fields` contents, partial update persistence, and 422 for `email`, `role`, `status`, `created_at`, or `skill_level`
- [X] T094 [P] [US3] Integration-test photo upload in `backend/tests/integration/test_profile_photo.py` — success with thumbnail, 413 over 5 MB, 415 for a renamed non-image, previous files deleted on replace, and the previous photo preserved when a rejected upload is attempted
- [X] T095 [P] [US3] Integration-test that one account cannot read or write another's profile, and that a Super Admin can read one, in `backend/tests/integration/test_profile_access.py`
- [X] T096 [P] [US3] Extend `backend/tests/integration/test_permission_matrix.py` with the `/me/profile` and `/media/photos` routes
- [X] T097 [P] [US3] Component-test the role-discriminated profile form in `frontend/tests/features/edit-own-profile.test.tsx`, asserting read-only fields render disabled and are absent from the submitted payload

### Implementation for User Story 3

- [X] T098 [P] [US3] Define the `PhotoStorage` protocol and its local filesystem implementation in `backend/src/app/services/ports/photo_storage.py` — store, read, delete, keyed by an unguessable name
- [X] T099 [P] [US3] Implement Pillow-based decode validation and 128×128 thumbnail generation in `backend/src/app/services/image_processing.py`, determining format by decoding rather than by declared content type or extension
- [X] T100 [US3] Define the profile schemas in `backend/src/app/schemas/profile.py` — `OwnProfile`, `OwnProfileUpdate`, the four role detail models, and `PhotoUrls` — with role detail as a discriminated union
- [X] T101 [US3] Add the profile read and update repository methods, including the role detail joins, in `backend/src/app/repositories/user_repository.py`
- [X] T102 [US3] Implement `ProfileService` in `backend/src/app/services/profile_service.py` — resolve the editable field set for a role, reject any write outside it, normalize the phone to E.164, and refuse edits to a Deleted account
- [X] T103 [US3] Implement photo upload, replacement with old-file deletion, and removal in `backend/src/app/services/profile_service.py`
- [X] T104 [US3] Implement `GET /me/profile`, `PATCH /me/profile`, `PUT /me/profile/photo`, and `DELETE /me/profile/photo` in `backend/src/app/api/v1/me_router.py`
- [X] T105 [US3] Implement the session-checked `GET /media/photos/{key}` with the `variant` parameter in `backend/src/app/api/v1/media_router.py`
- [X] T106 [P] [US3] Implement the own-profile query and mutation hooks, invalidating both `ownProfile` and `session`, in `frontend/src/entities/user/api/use-own-profile.ts`
- [X] T107 [US3] Build the role-discriminated `ownProfileSchema` and the edit form in `frontend/src/features/profile/edit-own/`, driving disabled state from the server's `editable_fields` rather than a local list
- [X] T108 [US3] Build the photo upload control with client-side size and type pre-checks and a default-avatar fallback in `frontend/src/features/profile/edit-own/ui/photo-field.tsx`
- [X] T109 [US3] Build the profile page and the `/profile` route in `frontend/src/pages/profile/` and `frontend/src/routes/_authed/profile.tsx`, with the shared form shell in `frontend/src/widgets/profile-form-shell/`

**Checkpoint**: US1–US3 all work independently. Every role can maintain its own profile.

---

## Phase 6: User Story 4 — Super Admin Deactivates and Reactivates a User (Priority: P2)

**Goal**: A Super Admin switches an account off — sign-in refused, open sessions dead within a minute, all history and reporting totals preserved — and can switch it back on.

**Independent Test**: Deactivate an account holding history and a live session; confirm sign-in refused, the session dies, the person still appears in records marked inactive, and totals are unchanged. Reactivate and confirm sign-in works with the existing password.

**Depends on**: US1 for sessions; US2 for the directory the actions are invoked from.

### Tests for User Story 4

- [X] T110 [P] [US4] Unit-test the last-active-Super-Admin guard and the self-action refusal in `backend/tests/unit/test_admin_guards.py`
- [X] T111 [P] [US4] Integration-test deactivation and reactivation in `backend/tests/integration/test_deactivate.py` — status change, sign-in refused with `account_not_active`, reactivation restoring access with the existing password, and 422 when already in the target status
- [X] T112 [P] [US4] Integration-test that every open session dies immediately on deactivation, in `backend/tests/integration/test_session_revocation.py` (FR-012, SC-007)
- [X] T113 [P] [US4] Integration-test the guards in `backend/tests/integration/test_admin_guards_api.py` — 422 `self_action_forbidden`, 422 `last_super_admin`, and success once a second active Super Admin exists
- [X] T114 [P] [US4] Integration-test optimistic concurrency in `backend/tests/integration/test_version_conflict.py` — a stale `version` returns 409 and changes nothing
- [X] T115 [P] [US4] Integration-test that an inactive account still appears in the directory marked inactive and that a seeded aggregate is unchanged across deactivation, in `backend/tests/integration/test_history_preserved.py` (FR-039, SC-008)
- [X] T116 [P] [US4] Extend `backend/tests/integration/test_permission_matrix.py` with the deactivate and reactivate routes
- [X] T117 [P] [US4] Component-test the confirmation dialogs in `frontend/tests/features/deactivate-user.test.tsx`, asserting the stated consequences appear and that cancelling changes nothing

### Implementation for User Story 4

- [X] T118 [US4] Add the transactional guard queries to `backend/src/app/repositories/user_repository.py` — count active Super Admins and apply a status change conditioned on the observed `version`, both inside the caller's transaction, with a comment on the row-lock needed if the store ever gains concurrent writers
- [X] T119 [US4] Define `StatusChangeRequest` in `backend/src/app/schemas/admin_user.py`
- [X] T120 [US4] Implement `UserAdminService.deactivate` in `backend/src/app/services/user_admin_service.py` — validate the transition, refuse self-action, refuse the last active Super Admin, bump `version`, revoke every session, and write the audit entry, all in one transaction
- [X] T121 [US4] Implement `UserAdminService.reactivate` in `backend/src/app/services/user_admin_service.py`, refusing a Deleted account with `erasure_is_permanent`
- [X] T122 [US4] Implement `POST /admin/users/{user_id}/deactivate` and `POST /admin/users/{user_id}/reactivate` in `backend/src/app/api/v1/admin_users_router.py`, translating `StaleVersion` to 409 and guard failures to 422 with their specific codes
- [X] T123 [P] [US4] Implement the deactivate and reactivate mutation hooks, invalidating `detail(userId)` and `all`, in `frontend/src/entities/user/api/use-user-status.ts`
- [X] T124 [US4] Build the deactivate and reactivate features with their confirmation dialogs in `frontend/src/features/admin/deactivate-user/` and `frontend/src/features/admin/reactivate-user/`, wording the prompt as FR-037 requires and driving open state from `pendingAction`
- [X] T125 [US4] Render inactive accounts as visibly marked, and show only the actions in `available_actions`, in `frontend/src/widgets/user-directory-table/`
- [X] T126 [US4] Surface the 409 stale-version case as a re-read prompt rather than a silent overwrite, in `frontend/src/features/admin/deactivate-user/`

**Checkpoint**: US1–US4 all work independently. Accounts can be switched off and on without losing history.

---

## Phase 7: User Story 5 — Super Admin Erases a User's Personal Information (Priority: P3)

**Goal**: A Super Admin permanently erases personal information with a stated reason; history and reporting totals survive exactly; the action cannot be undone and is recorded for compliance.

**Independent Test**: Erase an account holding history; confirm personal fields anonymized, historical records intact as "Deleted User", totals numerically unchanged, reactivation refused, and the compliance record complete and Super-Admin-only.

**Depends on**: US1, US2, and US4 (erasure operates on both Active and Inactive accounts).

### Tests for User Story 5

- [X] T127 [P] [US5] Unit-test the anonymization mapping in `backend/tests/unit/test_anonymization.py`, asserting every column in data-model.md §10 including that `skill_level` and `business_name` are deliberately retained
- [X] T128 [P] [US5] Integration-test erasure in `backend/tests/integration/test_erasure.py` — anonymized values, 422 without a reason, sessions revoked, invitations superseded, photo files deleted, and reactivation and profile edit both refused
- [X] T129 [P] [US5] Integration-test that a seeded aggregate is numerically identical before and after erasure and that historical rows remain attributed to "Deleted User", in `backend/tests/integration/test_erasure_history.py` (FR-046, FR-047, SC-009)
- [X] T130 [P] [US5] Integration-test email release and placeholder reservation in `backend/tests/integration/test_erasure_email.py` — the former address is reusable, and creating an account with a `deleted_*@example.com` address is rejected
- [X] T131 [P] [US5] Integration-test the compliance record in `backend/tests/integration/test_erasure_record.py` — complete contents for a Super Admin, 403 for every other role, and absence from all ordinary account views
- [X] T132 [P] [US5] Integration-test that erasing the last active Super Admin and erasing one's own account are both refused, in `backend/tests/integration/test_erasure_guards.py`
- [X] T133 [P] [US5] Extend `backend/tests/integration/test_permission_matrix.py` with the erase and erasure-record routes
- [X] T134 [P] [US5] Component-test the erasure dialog in `frontend/tests/features/erase-user.test.tsx` — the warning text, the required reason, and confirmation being blocked until a reason is entered

### Implementation for User Story 5

- [X] T135 [P] [US5] Implement the erasure repository in `backend/src/app/repositories/erasure_repository.py` — insert a compliance record and fetch one by user, with no method that joins it into an account read
- [X] T136 [US5] Define `EraseUserRequest` and `ErasureRecord` in `backend/src/app/schemas/admin_user.py`
- [X] T137 [US5] Implement `ErasureService.erase` in `backend/src/app/services/erasure_service.py` — one transaction applying the full §10 mapping, deriving the placeholder email from the account id, revoking sessions, superseding invitations, writing the compliance record and the audit entry, and refusing self-action, the last active Super Admin, and an already-Deleted account
- [X] T138 [US5] Delete both stored image files as part of the erasure transaction in `backend/src/app/services/erasure_service.py`, tolerating an already-missing file rather than failing the erasure
- [X] T139 [US5] Implement `POST /admin/users/{user_id}/erase` and `GET /admin/erasure-records/{user_id}` in `backend/src/app/api/v1/admin_users_router.py`
- [X] T140 [P] [US5] Implement the erase mutation hook, invalidating `detail(userId)`, `all`, and `erasureRecord(userId)`, in `frontend/src/entities/user/api/use-erase-user.ts`
- [X] T141 [US5] Build the erasure feature in `frontend/src/features/admin/erase-user/` — the prominent irreversible-action warning from FR-043, a required reason field, and confirmation disabled until it is filled
- [X] T142 [US5] Render an erased account's detail view as anonymized with all actions withdrawn, in `frontend/src/pages/admin-users/`

**Checkpoint**: All five stories work independently. The feature is functionally complete.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T143 Write the contract test comparing the generated OpenAPI document to `specs/001-user-roles-admin/contracts/openapi.yaml` in `backend/tests/contract/test_openapi_contract.py`, failing on any drift in paths, schemas, or status codes
- [X] T144 Review `backend/tests/integration/test_permission_matrix.py` for completeness — every role against every route registered in the app, discovered from the route table rather than hand-listed, so a new endpoint cannot be added without a permission assertion
- [X] T145 [P] Implement the maintenance routine pruning expired sessions and old sign-in attempts in `backend/src/app/services/maintenance_service.py`, exposed as a CLI command in `backend/src/app/cli.py`
- [X] T146 [P] Implement the `seed-users` command in `backend/src/app/cli.py` for the 10,000-account directory performance check
- [X] T147 Verify SC-006 by timing the first filtered directory page against 10,000 seeded accounts, and record the measurement in `specs/001-user-roles-admin/quickstart.md` §5
- [X] T148 [P] Add a test asserting no response body in any failure path contains a stack trace, driver message, or credential material, in `backend/tests/integration/test_no_internal_leakage.py` (SC-012)
- [X] T149 [P] Add a test asserting `UPDATE` and `DELETE` against `audit_entries` are rejected by the trigger, in `backend/tests/integration/test_audit_append_only.py` (FR-055)
- [X] T150 [P] Add structured request logging with the acting account id and never the request body, in `backend/src/app/core/logging.py`
- [X] T151 [P] Accessibility pass over the forms, dialogs, and table — labels, focus management, keyboard operation of the confirmation dialogs — across `frontend/src/features/` and `frontend/src/widgets/`
- [X] T152 [P] Add loading, empty, and error states to the directory and profile views in `frontend/src/widgets/user-directory-table/` and `frontend/src/pages/profile/`
- [X] T153 [P] Verify the two constitution greps from quickstart.md §6 return nothing — no raw SQL outside `db/engine.py`, no axios import outside `shared/api` — and add them to the CI script in `.github/workflows/ci.yml`
- [X] T154 Run the full quality gate from quickstart.md §6 — ruff, mypy strict, pytest, ESLint, `tsc --noEmit`, Vitest — and fix every finding
- [X] T155 Walk every scenario in quickstart.md §4 manually and reconcile any divergence between documented and actual behaviour
- [X] T156 [P] Write `backend/README.md` and `frontend/README.md` covering setup, the environment variables, and the layering and FSD rules a contributor must follow

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **blocks every user story**
- **US1 (Phase 3)**: Depends on Foundational only
- **US2 (Phase 4)**: Depends on US1 — a Super Admin must be able to sign in before creating anyone
- **US3 (Phase 5)**: Depends on US1 for sessions; needs US2 in practice to exercise all four roles
- **US4 (Phase 6)**: Depends on US1 for sessions and US2 for the directory
- **US5 (Phase 7)**: Depends on US1, US2, and US4 — erasure operates on Active and Inactive accounts
- **Polish (Phase 8)**: Depends on all stories being complete

### User Story Dependencies

These stories are **not** fully independent, and the reason is structural rather than an oversight:
every story after US1 is reached through an authenticated Super Admin session, and US2 is the only
way accounts come into existence. The spec's Independent Test for each story still holds — each is
separately demonstrable and separately testable once its prerequisite exists — but they cannot be
built in parallel by different people from a standing start.

```
Setup → Foundational → US1 ──┬──▶ US2 ──┬──▶ US4 ──▶ US5
                             │          │
                             └──────────┴──▶ US3
```

US3 and US4 are genuinely parallel once US2 lands: they touch different services, different routers,
and different frontend slices.

### Within Each User Story

- Tests are written first and must fail before implementation
- Repositories before services, services before routers — the constitution's dependency direction
- Backend endpoint before the frontend slice that calls it
- Story complete and its checkpoint validated before starting the next priority

### Parallel Opportunities

- Setup: T003, T004, T005, T006, T009–T014 are independent files
- Foundational: the four model modules T019–T023 are independent; T032, T036, T037, T038, T040, T042 are independent. Migrations T024–T027 are strictly sequential — Alembic revisions form a chain
- Every story's test tasks are marked [P] and can be written concurrently
- Repositories within a story are independent of one another; services are not, since several share `user_admin_service.py`
- Across stories: once US2 is complete, US3 and US4 can proceed concurrently

### Same-File Serialization

These tasks touch a shared file and must not be parallelized despite belonging to different phases:

- `backend/src/app/repositories/user_repository.py` — T055, T078, T101, T118
- `backend/src/app/services/user_admin_service.py` — T080, T081, T120, T121
- `backend/src/app/services/auth_service.py` — T056, T082
- `backend/src/app/api/v1/admin_users_router.py` — T084, T085, T122, T139
- `backend/src/app/api/v1/auth_router.py` — T060, T083
- `backend/src/app/schemas/admin_user.py` — T079, T119, T136
- `backend/tests/integration/test_permission_matrix.py` — T047, T073, T096, T116, T133, T144
- `frontend/src/widgets/user-directory-table/` — T088, T125, T152

---

## Parallel Example: User Story 1

```bash
# All US1 tests together — different files, no dependencies:
Task: "Unit-test the password policy in backend/tests/unit/test_password_policy.py"
Task: "Unit-test the rate limiter in backend/tests/unit/test_rate_limit.py"
Task: "Unit-test the status-transition map in backend/tests/unit/test_status_transitions.py"
Task: "Integration-test /auth/* in backend/tests/integration/test_auth.py"
Task: "Integration-test the permission matrix in backend/tests/integration/test_permission_matrix.py"
Task: "Integration-test the sign-in rate limit in backend/tests/integration/test_signin_rate_limit.py"
Task: "Component-test the sign-in form in frontend/tests/features/sign-in.test.tsx"
Task: "Component-test the route guards in frontend/tests/routes/guards.test.tsx"

# Then the independent US1 building blocks:
Task: "Implement hashing and token generation in backend/src/app/core/security.py"
Task: "Add the breached-password list and policy in backend/src/app/core/password_policy.py"
Task: "Implement the session repository in backend/src/app/repositories/session_repository.py"
Task: "Implement the sign-in attempt repository in backend/src/app/repositories/sign_in_attempt_repository.py"
```

## Parallel Example: Foundational Models

```bash
# The four model modules are independent — write them together, then chain the migrations:
Task: "Define the role and status enums in backend/src/app/models/enums.py"
Task: "Define users and user_profiles in backend/src/app/models/user.py"
Task: "Define the four role detail tables in backend/src/app/models/role_details.py"
Task: "Define sessions, invitations, and sign-in attempts in backend/src/app/models/auth.py"
Task: "Define audit_entries and erasure_records in backend/src/app/models/audit.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational — **critical, blocks everything**
3. Complete Phase 3: User Story 1
4. **Stop and validate**: run the US1 block of quickstart.md §4, including the permission matrix
5. Demo: four roles sign in, each lands in its own area, boundaries hold under direct request

US1 is a genuine MVP. It is the only slice that delivers standalone value with nothing before it, and
it is what every other epic in the project is waiting on.

One caveat worth planning around: US1's demo needs accounts in all four roles, and US2 is what
creates them. Until US2 lands, seed them with the bootstrap command plus a test fixture.

### Incremental Delivery

1. Setup + Foundational → both applications run, schema exists
2. + US1 → sign-in and permissions → **MVP, demo this**
3. + US2 → onboarding works end to end; the platform can be populated
4. + US3 → accounts become self-maintaining
5. + US4 → operational control over access without data loss
6. + US5 → privacy compliance
7. + Polish → contract test, performance verification, hardening

Each step leaves the platform working and adds value without breaking what came before.

### Parallel Team Strategy

With three developers:

1. Everyone on Setup + Foundational — it blocks all work, so finishing it fast matters most
2. US1 together — it is the narrowest path and everything queues behind it
3. Once US2 lands, split: one developer on US3 (profile, photos, `me_router`), one on US4 (status
   transitions, guards, directory actions), one starting Phase 8's contract and matrix tests
4. US5 after US4, since erasure operates on Inactive accounts

Do not split US1 and US2 across people. They share `auth_service.py` and `auth_router.py`, and the
merge cost exceeds the parallel gain.

---

## Notes

- Every task above names a real file path from plan.md §Project Structure — no task requires guessing where code goes
- [P] means a different file and no dependency on incomplete work; check the Same-File Serialization list before parallelizing anything
- Tests are written first within each story and must be seen to fail
- Commit after each task or logical group; the constitution requires ticking tasks off here as they land
- Every checkpoint is a valid stopping point for validation or demo
- Two raw-SQL sites are permitted and only two: T016's pragmas and T027's triggers. Any third is a constitution violation — T153's grep is what catches it

---

## Fixes

**Added**: 2026-08-25 | **Source**: post-implementation bug report against WIP commit `df1bdf3`

Six defects were reported after Phases 1–8 landed. Each is traced to a verified root cause below and
addressed here. Numbering continues from T156; **no existing task is renumbered or altered.**

### Format for this phase: `[ID] [P?] [Fix] Description`

- **[P]**: Can run in parallel — different files, no dependency on incomplete work
- **[Fix]**: Which reported defect the task belongs to (F1–F6):

| Marker | Reported defect | Verified root cause |
|---|---|---|
| **F1** | Empty-string values in form inputs; invalid-input messages not shown | No shared empty-string→null normalizer exists in `shared/lib`, so `''` crosses the network for every optional field (Principle VI); 11 nullable fields in `OwnProfileUpdate` carry no `min_length=1`; `''` for `phone` hard-fails in `_normalize_phone`; and no form except set-password maps a 422 `fields[]` onto its fields |
| **F2** | Photo upload broken; photo not shown on the profile page | `photo_url`/`thumbnail_url` are **API-relative** paths that only resolve against the axios `baseURL`; putting the raw value into a DOM `src` resolves it against the document origin instead, where the dev proxy forwards only `/api` |
| **F3** | Back buttons missing | No back affordance exists except one hardcoded `<Link>` on the user detail page, which discards the directory's search params; and no persistent chrome exists at all — `routes/_authed.tsx` renders a bare `<Outlet/>`, so each page invents its own header or has none |
| **F4** | Search field requests on every key press | The directory search input calls `navigate` synchronously in `onChange`, minting a new query key — and a new history entry — per keystroke |
| **F5** | Forms validate on every change instead of on submit | All four forms register the Zod schema under `validators: { onChange }` and gate the submit button on `canSubmit` |
| **F6** | Email sending service unfinished | `EMAIL_BACKEND=smtp` starts with no `SMTP_HOST`; TLS mode and timeout are hard-coded; the envelope `From` has a hard-coded production fallback; and the re-invite path reports success regardless of `invitation_sent` |

**Constitution note**: F1 discharges the standing `TODO(NULL_NORMALIZATION_HELPER)` recorded in
`.specify/memory/constitution.md` v1.1.0 — Principle VI requires exactly one normalizer in
`shared/lib`, and the frontend has none. T157 creates it and T171–T174 migrate every TanStack Form
submit path onto it, which is also the merge gate in Development Workflow §2.

---

### Fix Phase A: Shared primitives (blocking prerequisites)

**Purpose**: Every later fix task consumes one of these. All five are new files with no dependency
on each other, so the whole group runs in parallel.

**⚠️ CRITICAL**: No task in Fix Phases B–G may begin until this phase is complete.

- [x] T157 [P] [F1] Create the single empty-string-to-null normalizer in `frontend/src/shared/lib/normalize-payload.ts` — converts any string that is empty or whitespace-only to `null`, recursing through nested objects and arrays, passing every other value through unchanged; no trimming of real values. This is the **only** normalizer permitted to exist (constitution Principle VI); per-form ternaries at the call site are forbidden
- [x] T158 [P] [F1] Create the shared form-error helpers in `frontend/src/shared/lib/form-errors.ts` — `fieldErrorText(errors: readonly unknown[]): string | null`, normalizing both Standard-Schema issue objects (`{ message }`) and plain string errors, and `toServerErrorMap(error: unknown): { form?: string; fields: Record<string, string> }`, built from `ApiError.fields` for feeding `form.setErrorMap({ onServer: ... })`. Narrow through `isApiError`, never `any`
- [x] T159 [P] [F2] Create the media URL resolver in `frontend/src/shared/api/media.ts` — `resolveMediaUrl(path: string | null): string | null` prefixing `apiClient.defaults.baseURL` so an API-relative `/media/photos/{key}` becomes a URL a DOM `src` can load. This is the only place a media path becomes DOM-usable; components must never concatenate the base URL themselves
- [x] T160 [P] [F4] Create the debounce hook in `frontend/src/shared/lib/use-debounced-callback.ts` — a typed `useDebouncedCallback<TArgs>(fn, delayMs)` that clears its pending timer on unmount and on delay change. No `any`, no `NodeJS.Timeout` leakage into the public signature
- [x] T161 [P] [F3] Create `frontend/src/shared/ui/back-button.tsx` — a `BackButton` taking a required typed `fallbackTo` route, calling `useRouter().history.back()` when `useCanGoBack()` is true and navigating to `fallbackTo` otherwise, so a deep-linked page still offers a way out. Uses `shared/ui/button` and `lucide-react`'s chevron; no route string is built by concatenation
- [x] T162 [P] [F1] [F2] [F4] Unit-test the four new shared primitives in `frontend/tests/shared/normalize-payload.test.ts`, `frontend/tests/shared/form-errors.test.ts`, `frontend/tests/shared/media.test.ts`, and `frontend/tests/shared/use-debounced-callback.test.ts` — including whitespace-only strings, nested arrays and objects, a string-valued field error, a `null` media path, and that a rapid burst of calls invokes the debounced function exactly once

**Checkpoint**: All five primitives exist and are unit-tested; nothing consumes them yet.

---

### Fix Phase B: Backend validation contract (F1)

**Purpose**: Close the Principle VI gaps and the FR-022 phone-format gap before the frontend starts
sending `null` instead of `''`, so the two sides never disagree mid-fix.

**Depends on**: nothing in Fix Phase A — this phase may run concurrently with it.

- [x] T163 [F1] Extract phone parsing and E.164 normalization out of `backend/src/app/services/profile_service.py` into a new `backend/src/app/core/phone.py`, raising the same field-attributed `ValidationFailure`, and **delete the two `print()` calls** at the top of the old `_normalize_phone` — they write the raw phone number to stdout, which is personal data in the logs and contradicts T150's "never the request body"
- [x] T164 [F1] Add `min_length=1` to every nullable string field in `OwnProfileUpdate` in `backend/src/app/schemas/profile.py` — `phone`, `address`, `website`, `description`, `bio`, `credentials`, `certifications`, `school`, `jersey_number`, `emergency_contact_name`, `emergency_contact_phone`, `emergency_contact_relation` — so `''` returns a field-attributed 422 instead of being persisted (constitution Principle VI, storage invariant)
- [x] T165 [F1] In the same file, make `first_name` and `last_name` reject an **explicit** `null` with a field-attributed 422 while still allowing omission — they map to `NOT NULL` columns, so today `{"first_name": null}` reaches `setattr` and surfaces as a 500 through the catch-all handler
- [x] T166 [F1] Repoint `ProfileService.update_own_profile` in `backend/src/app/services/profile_service.py` at `app.core.phone`, and keep the `is not None` guard so an explicit `null` still clears the column while a real value is normalized (Principle VI: explicit null clears, omitted key untouched)
- [x] T167 [F1] Enforce phone format on the creation path — add the E.164 validator from `app.core.phone` to `CreateUserRequest.phone` in `backend/src/app/schemas/admin_user.py` and store the normalized value in `UserAdminService.create_user` in `backend/src/app/services/user_admin_service.py`. FR-022 and data-model.md §12 require the same rule the profile path already applies; only the profile path applies it today
- [x] T168 [P] [F1] Unit-test `backend/src/app/core/phone.py` in `backend/tests/unit/test_phone.py` — a parseable international number normalizes to E.164, an unparseable string and a valid-looking but invalid number both raise with the error attributed to `phone`, and the empty string is rejected rather than crashing
- [x] T169 [P] [F1] Extend `backend/tests/integration/test_own_profile.py` with the null-contract cases the merge gate requires: `''` for each nullable field returns 422 naming that field; an explicit `null` clears the column to SQL `NULL`; an omitted key leaves the column unchanged; and `{"first_name": null}` returns 422, not 500
- [x] T170 [P] [F1] Extend `backend/tests/integration/test_create_user.py` with a malformed phone returning 422 attributed to `phone`, and a valid national-format number being stored in E.164

**Checkpoint**: No nullable text column can hold `''`, an explicit `null` clears, and both write paths validate the phone identically.

---

### Fix Phase C: Form validation timing and error display (F1, F5)

**Purpose**: Validate on submit, then live-revalidate; show each offending field's message beside
that field, from both Zod and the server.

**Depends on**: Fix Phase A (T157, T158) and Fix Phase B (the 422 shapes these forms render).

Each form is a separate file, so the four migrations run in parallel. Every one of them applies the
same three changes: swap `validators: { onChange: schema }` for
`validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' })` plus
`validators: { onDynamic: schema }` (supported by the installed `@tanstack/react-form` 1.33.5);
render field errors through `fieldErrorText` instead of the inline
`errors.map((e) => e?.message).join(', ')`, which silently renders nothing for a string-valued
error; and drop `canSubmit` from the submit button's `disabled` expression, keeping `isSubmitting`,
so submitting is what reveals the errors.

- [x] T171 [P] [F5] Migrate `frontend/src/features/auth/sign-in/ui/sign-in-form.tsx` to submit-time validation and `fieldErrorText`
- [x] T172 [P] [F5] Migrate `frontend/src/features/auth/set-password/ui/set-password-form.tsx`, and replace its one-off `fieldMessage('password')` call with `form.setErrorMap({ onServer: toServerErrorMap(error) })` so the breached-password and policy failures land on the field generically
- [x] T173 [P] [F1] [F5] Migrate `frontend/src/features/admin/create-user/ui/create-user-form.tsx`, add `form.setErrorMap({ onServer: ... })` on mutation error so a 422 names the offending field instead of collapsing to "One or more fields are invalid.", and route the payload through `normalizeEmptyToNull` — the conditional `business_name` spread stays, but no field may leave as `''`
- [x] T174 [P] [F1] [F5] Migrate `frontend/src/features/profile/edit-own/ui/edit-profile-form.tsx`, route the submitted values through `normalizeEmptyToNull`, and add `form.setErrorMap({ onServer: ... })`. This is the task that makes a cleared optional field actually clear it, and that lets a user with no phone number save their profile at all
- [x] T175 [F1] [F5] Update `frontend/tests/features/sign-in.test.tsx`, `create-user.test.tsx`, and `edit-own-profile.test.tsx` for the new timing — assert no error text appears while typing before the first submit, that submitting an invalid form reveals the per-field message, that a 422 `fields` entry renders next to its own input, and that an untouched optional field is submitted as `null` rather than `''`

**Checkpoint**: No form shows an error before its first submit, every 422 field message is visible beside its input, and no `''` leaves the browser.

---

### Fix Phase D: Profile photo (F2)

**Depends on**: Fix Phase A (T159).

- [x] T176 [F2] Resolve the photo URL through `resolveMediaUrl` in `frontend/src/pages/profile/index.tsx` before passing it to `PhotoField`, so `<AvatarImage>` receives a URL the browser can load rather than an API-relative path that 404s against the dev server and silently falls back to the initials
- [x] T177 [F2] In `frontend/src/features/profile/edit-own/ui/photo-field.tsx`, stop hard-rejecting on `file.type` when it is empty or unrecognized — the browser derives it from the extension, and R-07 makes the decoded bytes the authority; keep the size pre-check and let an unsupported format come back as the server's 415
- [x] T178 [F2] Remove the hand-set `'Content-Type': 'multipart/form-data'` header from `useUploadOwnPhoto` in `frontend/src/entities/user/api/use-own-profile.ts` — axios unsets it for browser `FormData` anyway, so it is inert today but is a boundary-less-multipart trap on any other adapter; let the browser set the header with its boundary
- [x] T179 [P] [F2] Component-test the photo control in `frontend/tests/features/photo-field.test.tsx` — a resolved URL is used as the image source, an oversized file is rejected without a request, a file with an empty `type` still reaches the server, and a 415 response surfaces as a message naming the accepted formats and size limit

**Checkpoint**: An uploaded photo appears on the profile page immediately after the mutation invalidates `ownProfile`.

---

### Fix Phase E: Directory search debounce (F4)

**Depends on**: Fix Phase A (T160). Must land **before** Fix Phase F, or every keystroke remains a separate back step.

- [x] T180 [F4] Debounce the search input in `frontend/src/widgets/user-directory-table/ui/user-directory-table.tsx` — hold the typed text in local component state seeded from `search.q`, push it into the URL through `useDebouncedCallback` at **500 ms** (interval decided by the user, 2026-08-25), and keep the URL the single source of truth for `q` (contracts/frontend-contracts.md §4); do not introduce a Zustand field or a second copy of the search term
- [x] T181 [F4] In the same file, navigate with `replace: true` for search-term changes so a 20-character query leaves one history entry instead of twenty, while paging and the role/status filters keep pushing a normal entry — those are deliberate steps a Super Admin should be able to reverse
- [x] T182 [P] [F4] Component-test the directory search in `frontend/tests/widgets/user-directory-table.test.tsx` with fake timers — typing a multi-character term issues exactly one `GET /admin/users`, the request carries the full term, and the role and status filters still apply immediately

**Checkpoint**: One request per settled search term; history is not flooded by typing.

---

### Fix Phase F: Navigation chrome and back affordance (F3)

**Scope widened 2026-08-25 by user decision**: the shared `BackButton` alone was the original scope;
the user chose the **app shell as well**, so this phase now delivers persistent chrome for every
authenticated page in addition to the per-page back affordance.

**Depends on**: Fix Phase A (T161) and Fix Phase E (T181 — until search-term navigation is
`replace: true`, a back affordance is worse than none, because one back press per keystroke is what
the user gets).

**⚠️ Task IDs in this phase are not in execution order.** T183–T186 were written before the scope
widened and are kept at their original numbers rather than renumbered; T199–T204 are the shell.
Execute in this order:

```
T161 (BackButton, Fix A) → T199 → T200 → T201 → T202 → T203 → T183 → T184 → T185 → T186, T204
```

**Where the shell lives**: `routes/_authed.tsx`, not `routes/__root.tsx`. The root route also
carries `/login` and `/set-password`, which must **not** show signed-in chrome — a sign-in page with
a sign-out button and a breadcrumb trail is wrong. `__root.tsx` is therefore untouched by this
phase and stays a bare `<Outlet/>`.

- [x] T199 [P] [F3] Add the shadcn/ui `breadcrumb` primitive to `frontend/src/shared/ui/breadcrumb.tsx` via the CLI, which `components.json` already aliases into `shared/ui` (T008). All shadcn primitives live in `shared/ui` and nowhere else (constitution Principle IV)
- [x] T200 [F3] Build the breadcrumb trail in `frontend/src/widgets/app-shell/model/use-breadcrumbs.ts` — derive the trail from the router's matched routes, emitting typed `to`/`params`/`search` link descriptors, never concatenated URL strings (Principle IV, routing rule). Carry the directory's search params on the `/admin/users` crumb so the trail returns to the filtered view, not a reset one
- [x] T201 [F3] Build `frontend/src/widgets/app-shell/ui/app-shell.tsx` — the persistent header: a `BackButton` slot, the breadcrumb region from T200, the signed-in person's name and role read from the `session` query, a typed `/profile` link, and the sign-out action from `features/auth/sign-out`. Composes `shared/ui` primitives only; holds no server state of its own and copies nothing into Zustand
- [x] T202 [F3] Render the shell around `<Outlet/>` in `frontend/src/routes/_authed.tsx`, leaving the existing `beforeLoad` session guard untouched — the guard is the reason the shell can assume a session exists and render the identity block without a loading branch
- [x] T203 [F3] Remove the now-duplicated header block from `frontend/src/pages/dashboard/index.tsx` — the identity heading, the `/profile` link, and the sign-out button all move into the shell; the page keeps only its per-role content. Two headers stacked on the landing page is the failure mode this prevents
- [x] T183 [F3] Add an optional `backTo` slot rendering `BackButton` to `frontend/src/widgets/profile-form-shell/ui/profile-form-shell.tsx`, and use it from `frontend/src/pages/profile/index.tsx` with `fallbackTo` of `/` — the profile page currently has no way back to the landing area
- [x] T184 [F3] Add `BackButton` with `fallbackTo` of `/` to the directory header in `frontend/src/pages/admin-users/index.tsx` (`UsersIndexPage`)
- [x] T185 [F3] Replace the hardcoded `<Link to="/admin/users">← Back to directory</Link>` in `UserDetailPage` in `frontend/src/pages/admin-users/index.tsx` with `BackButton` and `fallbackTo` of `/admin/users` — the hardcoded link discards the directory's page, search term, and filters, which contradicts contracts/frontend-contracts.md §4's reason for putting that state in the URL at all
- [x] T186 [P] [F3] Component-test back navigation in `frontend/tests/shared/back-button.test.tsx` — history back is used when there is history, `fallbackTo` is navigated to when there is not, and returning from a user detail restores the directory's filters
- [x] T204 [P] [F3] Component-test the shell in `frontend/tests/widgets/app-shell.test.tsx` — the header renders on every authenticated route and on none of the public ones, the breadcrumb trail matches the active route, the `/admin/users` crumb carries the active filters, and sign-out is reachable from the shell rather than from a page

**Checkpoint**: Every authenticated page carries the same chrome, every page below the landing area offers a way back, and returning to the directory preserves the filtered view.

---

### Fix Phase G: Email sending service (F6)

**Purpose**: Finish the port R-11 specified. The interface, both implementations, and the injection
wiring already exist; configuration validation, transport options, and failure visibility do not.

**Depends on**: nothing in Fix Phases A–F — this phase may run concurrently.

- [x] T187 [F6] Add a `model_validator(mode="after")` to `Settings` in `backend/src/app/core/config.py` requiring `smtp_host` and `smtp_from_address` when `email_backend == "smtp"`, so a misconfigured relay fails at startup instead of turning every invitation into a swallowed exception and a silent `invitation_sent: false`
- [x] T188 [F6] Add `smtp_tls: Literal["starttls", "implicit", "none"] = "starttls"` and `smtp_timeout_seconds: int = 10` to `Settings` in `backend/src/app/core/config.py` — the current implementation hard-codes STARTTLS, which cannot reach an implicit-TLS relay on 465 or a local Mailpit/MailHog on 1025
- [x] T189 [F6] Map the three TLS modes and the timeout onto the `aiosmtplib.send` call in `backend/src/app/services/ports/email_sender.py`, and **remove the `or "noreply@example.org"` fallback** for the envelope `From` — a hard-coded production default is exactly what the settings class's own docstring forbids. Keep the bool return and the caught-and-logged failure: R-11's in-request send with a Super-Admin-visible failure stands
- [x] T190 [F6] Update `backend/.env.example` with `SMTP_TLS` and `SMTP_TIMEOUT_SECONDS`, and state in the comments which keys become mandatory when `EMAIL_BACKEND=smtp`; reflect the same in the environment table in `backend/README.md`
- [x] T191 [F6] Surface a failed re-invitation in `frontend/src/features/admin/reinvite-user/ui/reinvite-button.tsx` — it currently toasts "Invitation re-sent" unconditionally, ignoring `invitation_sent` in the response, so a delivery failure reads as success and the Super Admin never re-tries. Report the failure and name re-invite as the retry, matching the wording the create path already uses
- [x] T192 [F6] Give `useReinviteUser` in `frontend/src/entities/user/api/use-users.ts` an explicit response type parameter on `apiClient.post` — the untyped call yields `any` for `data`, which Principle II forbids anywhere in the frontend
- [x] T193 [P] [F6] Unit-test both senders in `backend/tests/unit/test_email_sender.py` — the filesystem sink writes a file containing the recipient, subject, and setup link and returns `True`; the SMTP sender returns `False` and logs rather than raising when the relay is unreachable; each TLS mode maps to the expected `aiosmtplib` arguments; and no rendered invitation body contains a password
- [x] T194 [P] [F6] Unit-test the settings guard in `backend/tests/unit/test_settings_validation.py` — `EMAIL_BACKEND=smtp` without `SMTP_HOST` or without `SMTP_FROM_ADDRESS` fails to construct `Settings`, and `EMAIL_BACKEND=filesystem` constructs without any SMTP key
- [x] T195 [P] [F6] Component-test the re-invite button in `frontend/tests/features/reinvite-user.test.tsx` — `invitation_sent: false` renders a failure message, `true` renders success

**Checkpoint**: A misconfigured mail relay is a startup error, a real relay is reachable under all three TLS modes, and non-delivery is visible to the Super Admin on both the create and re-invite paths.

---

### Fix Phase H: Regression gates

**Depends on**: all of Fix Phases A–G.

- [x] T196 [F1] Add a grep gate to `.github/workflows/ci.yml` alongside T153's two — assert that `normalize-payload` is imported by every file containing `onSubmit:` under `frontend/src/features/`, and that no second normalizer or inline `|| null` / `? x : null` empty-string conversion exists at a submit call site. Principle VI permits exactly one normalizer, and a second one is the failure mode this catches
- [x] T197 Run the full quality gate from quickstart.md §6 — ruff, mypy strict, pytest, ESLint including the boundaries rule, `tsc -b --noEmit`, Vitest — and fix every finding introduced by T157–T196
- [x] T198 Walk the affected quickstart.md §4 scenarios end to end — US2 creation with a bad phone and a duplicate email, US3 profile save with an empty optional field and a photo upload, the directory search, and back navigation from a user detail — and reconcile any divergence between documented and actual behaviour

---

### Fixes: Dependencies & Execution Order

```
Fix A (T157–T162) ──┬──▶ Fix C (T171–T175) ─────────────────────────────┐
                    ├──▶ Fix D (T176–T179) ─────────────────────────────┤
                    ├──▶ Fix E (T180–T182) ──▶ Fix F (T199–T203,        │
                    │                                  T183–T186, T204) ├──▶ Fix H (T196–T198)
Fix B (T163–T170) ──┴──▶ Fix C                                          │
Fix G (T187–T195) ──────────────────────────────────────────────────────┘
```

- **Fix A and Fix B are the only entry points** and are independent of each other; Fix G is independent of both and can be picked up by a third developer immediately
- **Fix C depends on both A and B** — it renders the errors B produces using the helpers A creates
- **Fix E must precede Fix F**: until T181 makes search-term navigation `replace: true`, a back button is worse than none, because one back press per keystroke is what the user gets
- **Fix D depends only on T159**
- **Within Fix F**, the shell (T199–T203) precedes the per-page back affordances (T183–T185), because the shell owns the region the `BackButton` renders into. T186 and T204 are the only `[P]` tasks in the phase

### Fixes: Same-File Serialization

Additions to the list above; these must not be parallelized despite sitting in different phases:

- `frontend/src/pages/admin-users/index.tsx` — T184, T185
- `frontend/src/pages/profile/index.tsx` — T176, T183
- `frontend/src/pages/dashboard/index.tsx` — T067, T203
- `frontend/src/routes/_authed.tsx` — T039, T202
- `frontend/src/widgets/app-shell/` — T200, T201 (`model/` and `ui/` are separate files, but T201 consumes T200's hook, so they are sequential, not parallel)
- `frontend/src/widgets/profile-form-shell/ui/profile-form-shell.tsx` — T109, T183
- `frontend/src/shared/ui/` — T040, T199 (a shadcn CLI `add` run; do not run it concurrently with any other `add`)
- `frontend/src/routes/__root.tsx` — **no fix task touches this file.** Recorded here so the omission is deliberate and reviewable: the shell belongs at `_authed`, because `__root` also carries `/login` and `/set-password`, which must not render signed-in chrome
- `frontend/src/widgets/user-directory-table/ui/user-directory-table.tsx` — T088, T125, T152, T180, T181
- `frontend/src/features/profile/edit-own/ui/photo-field.tsx` — T108, T177
- `frontend/src/entities/user/api/use-own-profile.ts` — T106, T178
- `frontend/src/entities/user/api/use-users.ts` — T086, T191, T192
- `frontend/src/features/profile/edit-own/ui/edit-profile-form.tsx` — T107, T174
- `frontend/src/features/admin/create-user/ui/create-user-form.tsx` — T087, T173
- `backend/src/app/schemas/profile.py` — T100, T164, T165
- `backend/src/app/schemas/admin_user.py` — T079, T119, T136, T167
- `backend/src/app/services/profile_service.py` — T102, T103, T163, T166
- `backend/src/app/services/user_admin_service.py` — T080, T081, T120, T121, T167
- `backend/src/app/core/config.py` — T015, T187, T188
- `backend/src/app/services/ports/email_sender.py` — T076, T189
- `backend/tests/integration/test_own_profile.py` — T093, T169
- `backend/tests/integration/test_create_user.py` — T068, T170

### Fixes: Specification approval state

**APPROVED AND MERGED — 2026-08-25.** Every open design question was decided by the user, and every
specification amendment this phase depends on has been applied. **Nothing in this phase is blocked;
implementation may begin.**

| Question | Decision | Tasks affected |
|---|---|---|
| Back navigation model | **App shell as well as the button** — persistent header and breadcrumbs, not a bare back button | T161 unblocked; T199–T204 added; T183–T185 kept |
| Debounce interval | **500 ms** | T180 unblocked and updated |
| Email transport | **SMTP only** — no HTTP-API sender, no outbox or retry worker | T187–T195 unblocked and confirmed in scope |
| Spec artifact edits | **Approved and applied** | all — see the requirement backing below |

Requirement backing now in place, so Principle I is satisfied for every task in this phase:

| Artifact | What landed |
|---|---|
| `spec.md` | **FR-057**–**FR-064** in three new groups (input validation and optional detail; presentation and navigation; invitation delivery), plus **SC-013** and **SC-014** |
| `plan.md` | Constitution Check re-evaluated against constitution v1.1.0, adding the Principle VI row as **FAIL as built**; new `## Post-Implementation Technical Decisions (Bug-Fix Slice)` section carrying **D-01**–**D-06** |
| `data-model.md` | Three rows in §12 — the nullable-text/null-clears rule, the required-name null rejection, and phone format on both write paths |
| `contracts/openapi.yaml` | `minLength: 1` on twelve nullable `OwnProfileUpdate` strings; null-clears semantics in its description; phone format on `CreateUserRequest`; API-relative declared on all six photo-URL properties |
| `contracts/frontend-contracts.md` | §3 the two cross-form obligations; §5 `media.ts`; §6 the must-derive table; new §7 on validation timing, server-error mapping, and navigation chrome |

Traceability from each fix group to its requirement:

| Fix | Requirements | Plan decision |
|---|---|---|
| F1 | FR-057, FR-058, FR-059; data-model §12 | D-01, D-02 |
| F2 | FR-060 | D-03 |
| F3 | FR-061, FR-062, SC-014 | D-05 |
| F4 | FR-063, SC-013 | D-04 |
| F5 | FR-057, FR-058 | D-02 |
| F6 | FR-064 | D-06 |

---

## Extension: ShareLink Onboarding, Multi-Trainer Association & Portal Branding

**Added**: 2026-08-26 | **Source**: spec.md User Stories 6–8, FR-065 – FR-104, SC-015 – SC-025 |
**Design**: plan.md §Extension, research.md Part C (R-21 – R-33), data-model.md §15–§24,
contracts/openapi.yaml v1.1.0, contracts/frontend-contracts.md §8–§14, quickstart.md US6–US8

Numbering continues from T204; **no existing task is renumbered or altered.** Every task below is
new work — nothing in this extension exists in the codebase today (verified against
`backend/src/app/` and `frontend/src/` on 2026-08-26).

### Format for this phase: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependency on incomplete work
- **[Story]**: US6, US7, or US8, matching spec.md. Extension-Foundational and Extension-Polish tasks
  carry no story label, because every story depends on them

| Story | Spec | Priority | Delivers |
|---|---|---|---|
| **US6** | User Story 6, FR-065 – FR-083 | P1 | A trainer's standing invitation link, and self-service registration into their roster |
| **US7** | User Story 7, FR-084 – FR-092 | P2 | One account across many trainers, with server-resolved context and provable isolation |
| **US8** | User Story 8, FR-093 – FR-104 | P3 | A trainer's logo and colour on the portal their players and coaches see |

**Tests are included**, on the same reasoning as the original phases: the constitution makes passing
tests a merge gate, and SC-017, SC-021, SC-023, and SC-025 each name a test as the thing that
proves them.

---

### Extension Phase A: Foundational (Blocking Prerequisites)

**Purpose**: The whole schema for the extension, its repositories, and the two pure primitives the
later phases consume.

**⚠️ CRITICAL**: No task in Extension Phases B–D may begin until this phase is complete.

- [X] T205 Add the `ShareLinkKind`, `AssociationStatus`, and `Gender` `StrEnum`s to `backend/src/app/models/enums.py`, persisted as constrained text like `UserRole` and `AccountStatus` (data-model §15). `coach_single_use` is declared but never written by this feature — FR-072 requires the distinction to exist now so US-01.08 is additive
- [X] T206 [P] Create the `share_links` model in `backend/src/app/models/share_link.py` per data-model §16 — unique index on `code`, composite index on `(trainer_user_id, is_active)`, and a comment recording that `code` is stored **in clear** unlike every other token here (research R-21)
- [X] T207 [P] Create the `trainer_player_associations` and `link_lookup_attempts` models in `backend/src/app/models/association.py` per data-model §17 and §18 — the unique constraint on `(trainer_user_id, player_user_id)` is what makes FR-082 true rather than checked, and `link_lookup_attempts` deliberately holds no foreign key
- [X] T208 Extend the `player_details` model in `backend/src/app/models/role_details.py` with `player_name`, `date_of_birth`, `gender`, `is_self`, and `active_trainer_user_id` (data-model §19.1)
- [X] T209 Extend the `trainer_organizations` model in `backend/src/app/models/role_details.py` with `logo_key`, `primary_color`, and `branding_updated_at` (data-model §19.2) — same file as T208, so these run in sequence
- [X] T210 Write Alembic revision `backend/migrations/versions/0005_create_share_links_and_associations.py` creating all three new tables with their check constraints and indexes (data-model §23)
- [X] T211 Write Alembic revision `backend/migrations/versions/0006_extend_player_details_and_branding.py` adding the eight columns, all nullable or server-defaulted so no table rewrite is needed; `is_self` takes a server default of `true` so existing player rows stay valid
- [X] T212 Write Alembic revision `backend/migrations/versions/0007_backfill_trainer_share_links.py` creating one `player_standing` link for every existing trainer that has none — **SQLAlchemy Core constructs against `op.get_bind()`, not raw SQL**, so the two documented exceptions in plan.md §Complexity Tracking stay at two. Codes are generated in Python during the migration so backfilled links carry the same entropy as new ones. Must be idempotent
- [X] T213 [P] Create `backend/src/app/repositories/share_link_repository.py` — lookup by code, current link for a trainer, insert, revoke, and an atomic use-count increment. Queries only; the usability predicate belongs to the service
- [X] T214 [P] Create `backend/src/app/repositories/association_repository.py` — insert, exists-by-pair, list by player, list by trainer with paging and a name filter, and count by trainer
- [X] T215 [P] Create `backend/src/app/repositories/link_lookup_attempt_repository.py` — insert an attempt, count unsuccessful attempts for a client address in a trailing window, mirroring `sign_in_attempt_repository`
- [X] T216 [P] Create `backend/src/app/services/svg_screening.py` — refuse any payload containing a `<!DOCTYPE` declaration **before parsing**, then parse with `xml.etree.ElementTree` and reject a `script` or `foreignObject` element, any attribute beginning `on`, and any `href`/`xlink:href` whose value does not begin `#`. Standard library only; adding a sanitizer dependency would require a constitution amendment (research R-27)
- [X] T217 [P] Write `backend/tests/unit/test_svg_screening.py` with a fixture set of hostile SVGs — inline `<script>`, `onload` attribute, `<foreignObject>` with an iframe, an external `xlink:href`, a DOCTYPE with an entity — plus clean SVGs that must pass unchanged
- [X] T218 [P] Create `frontend/src/shared/lib/brand-palette.ts` — a pure `brandPalette(primaryHex: string)` returning CSS custom property values: the chosen colour unchanged for borders, gradient stops, and focus rings, and lightness-adjusted variants for any surface carrying text, walking until the token foreground clears a 4.5:1 WCAG contrast ratio (research R-29). No `any`
- [X] T219 [P] Write `frontend/tests/shared/brand-palette.test.ts` sweeping several hundred colours — including the mid-tone band where neither black nor white text reaches 4.5:1 against the raw colour — and asserting every returned text-bearing surface clears 4.5:1. **This test is SC-023**
- [X] T220 [P] Add `PUBLIC_APP_BASE_URL` to the settings class in `backend/src/app/core/config.py` and to `backend/.env.example` — the absolute join URL is assembled from it, and a hard-coded fallback is exactly what the configuration rule forbids
- [X] T221 [P] Add the extension's domain errors to `backend/src/app/core/errors.py` and their HTTP translations — `invitation_link_invalid` (404), `role_cannot_join` (403), `link_lookup_throttled` (429), `trainer_context_not_found` (404). The link error carries **one** message for all five refusal causes (FR-070)
- [X] T222 [P] Add the extension's contract types to `frontend/src/shared/api/types.ts`, mirroring the new `openapi.yaml` schemas exactly — `ShareLink`, `JoinLinkPreview`, `JoinRegistrationRequest`, `JoinResult`, `TrainerContextList`, `PortalBranding`, `TrainerPlayerPage`, and the `Gender` and `viewer.state` unions as closed string unions rather than `string`
- [X] T223 [P] Create the query-key factories in `frontend/src/entities/join/api/query-keys.ts` and `frontend/src/entities/trainer-context/api/query-keys.ts`, and extend `frontend/src/entities/user/api/query-keys.ts` with `trainers`, `shareLink`, and `branding` (frontend-contracts §9). The `['ctx', trainerId, …]` namespace is the standing convention Epics 02–08 inherit — every context-scoped key goes under it
- [X] T224 [P] Write `backend/tests/integration/test_migration_backfill.py` asserting that `alembic upgrade head` run twice leaves exactly one active standing link per trainer, and that every backfilled code is unique and at least 22 characters

**Checkpoint**: `alembic upgrade head` creates 12 tables and backfills a link for every existing
trainer; the two pure primitives are unit-tested; nothing consumes them yet.

---

### Extension Phase B: User Story 6 — Joining a Trainer Through an Invitation Link (Priority: P1) 🎯 Extension MVP

**Goal**: A trainer holds one durable link. Anyone who opens it sees a join page naming that trainer
and registers into their roster in a single transaction, arriving signed in and in that trainer's
area.

**Independent Test**: Create a trainer, take their link, open it in a browser with no session,
register, and confirm the new person is signed in and sees that trainer while the trainer sees them
on the roster. Delivers self-service player onboarding with nothing else from the extension shipped.

#### Tests for User Story 6

- [X] T225 [P] [US6] Write `backend/tests/unit/test_share_link_service.py` covering the five-part usability predicate — inactive, revoked, expired, exhausted, and owner-not-Active each refuse, and a healthy link admits
- [X] T226 [P] [US6] Write `backend/tests/integration/test_join_preview.py` asserting a valid code returns only business name, branding, and `viewer.state`, and that an unknown code and a revoked code produce **byte-identical** 404 bodies (FR-070)
- [X] T227 [P] [US6] Write `backend/tests/integration/test_join_register.py` covering the happy path — account, profile, player detail, parent contact, association, and session all created, `use_count` raised by exactly one, cookie set — plus an induced mid-transaction failure asserting **nothing** persists (FR-083)
- [X] T228 [P] [US6] Write `backend/tests/integration/test_join_validation.py` covering `is_self` age bands (self under 18 refused, dependant over 18 refused), the missing `player_name` when `is_self` is false, the duplicate-email 409, and an empty string for any optional field returning 422 rather than being stored (Principle VI)
- [X] T229 [P] [US6] Write `backend/tests/integration/test_join_link_throttle.py` asserting the 11th unsuccessful lookup from one origin returns 429 with `Retry-After`, that the window slides so access resumes without intervention, and running the 10,000-invalid-code trial that **is SC-021**
- [X] T230 [P] [US6] Write `backend/tests/integration/test_trainer_roster.py` asserting a trainer sees only their own players, that paging and the name filter work, and that no field of any response names another trainer
- [X] T231 [P] [US6] Write `frontend/tests/pages/join.test.tsx` with MSW, asserting all four `viewer.state` branches render their own affordance and that the registration form appears only for `anonymous`

#### Implementation for User Story 6

- [X] T232 [P] [US6] Create `backend/src/app/schemas/share_link.py` with the `ShareLink` response model matching `openapi.yaml`, assembling the absolute `url` from `PUBLIC_APP_BASE_URL`
- [X] T233 [P] [US6] Create `backend/src/app/schemas/join.py` with `JoinLinkPreview`, `JoinRegistrationRequest`, and `JoinResult` — every nullable string carries `min_length=1`, and the age-band rule is a `model_validator` across `is_self` and `date_of_birth` so its message attaches to `date_of_birth`
- [X] T234 [US6] Create `backend/src/app/services/share_link_service.py` — issue a standing link, read the trainer's current one, regenerate (revoke plus insert in one transaction), and the single usability predicate T225 tests. No router and no repository decides usability
- [X] T235 [US6] Extend `backend/src/app/services/user_admin_service.py` so creating a Trainer issues that trainer's standing link **in the same transaction** as the account (research R-22) — a lazy first-read creation would turn a `GET` into a write and take the SQLite write lock
- [X] T236 [US6] Add the per-origin lookup throttle to `backend/src/app/services/share_link_service.py` over `link_lookup_attempt_repository` — 10 unsuccessful lookups per 15 minutes, sliding, recording successes too so the window clears
- [X] T237 [US6] Create `backend/src/app/services/join_service.py` with the registration transaction of research R-23 — account, profile, player detail, parent contact, association, use-count increment, and session inside one `async with session.begin()`. The duplicate email is caught as an `IntegrityError` on the existing unique index and translated, never pre-checked
- [X] T238 [US6] Add the join confirmation email template to `backend/src/app/services/templates/` and send it from `join_service` through the existing `EmailSender` port, naming the trainer. A delivery failure must not undo the registration, must be recorded, and must not be reported as success (FR-079)
- [X] T239 [US6] Create `backend/src/app/api/v1/join_router.py` with `GET /join/{code}` and `POST /join/{code}/register`, both **unauthenticated** (`security: []` in the contract), resolving `viewer.state` server-side — the client must not infer it (frontend-contracts §14)
- [X] T240 [US6] Add `GET /me/share-link` and `POST /me/share-link/regenerate` to `backend/src/app/api/v1/me_router.py`, gated to the Trainer role through the existing role dependency
- [X] T241 [US6] Create `backend/src/app/api/v1/trainer_router.py` with `GET /trainer/players`, plus its `TrainerPlayerSummary`/`TrainerPlayerPage` schemas — the response carries **nothing** about a player's other trainers, not an identifier and not a count (FR-090)
- [X] T242 [US6] Add the roster query to `backend/src/app/repositories/association_repository.py` — joined to profile and player detail, rendering an erased account as "Deleted User" (FR-091) and deriving age from `date_of_birth` rather than storing it (research R-31)
- [X] T243 [US6] Register `join_router` and `trainer_router` in `backend/src/app/main.py`, and confirm the public routes sit outside the session dependency
- [X] T244 [US6] Add the `seed-demo-trainer` command to `backend/src/app/cli.py`, printing one trainer's credentials and standing join URL — without it, obtaining a link from a cold start requires signing in as a trainer first, which is the loop quickstart US6 needs to break
- [X] T245 [P] [US6] Create the join preview query hook in `frontend/src/entities/join/api/use-join-preview.ts` using `joinKeys.preview(code)`
- [X] T246 [P] [US6] Create `joinRegistrationSchema` in `frontend/src/features/join/register/model/schema.ts`, mirroring `JoinRegistrationRequest` — the age band is a cross-field refinement attached to `date_of_birth`, matching the backend validator exactly (frontend-contracts §10)
- [X] T247 [US6] Build the registration form in `frontend/src/features/join/register/ui/join-register-form.tsx` — TanStack Form with `revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' })`, the payload routed through the **existing** `normalizeEmptyToNull`, errors rendered through `fieldErrorText`, and a 422 mapped with `toServerErrorMap`. No second normalizer (Principle VI)
- [X] T248 [US6] Create `frontend/src/pages/join/index.tsx` and `frontend/src/routes/join.$code.tsx` — a **public** route beside `login.tsx`, not under `_authed`, which would redirect away the very visitor the page exists for. Branch on `viewer.state`, never on a local reading of the session
- [X] T249 [P] [US6] Build the share-link panel in `frontend/src/features/trainer/share-link/` — display, copy-to-clipboard, and regenerate with a confirmation that names what regenerating does and does not break
- [X] T250 [US6] Create the trainer area shell — `frontend/src/routes/_authed/trainer.tsx` as a layout route with a 403 view unless the role is `trainer`, plus `frontend/src/routes/_authed/trainer/portal.tsx` and `frontend/src/pages/trainer-portal/index.tsx` carrying the link panel. Branding joins this page in US8; it is one screen, as the epic's "My Portal Settings" describes
- [X] T251 [P] [US6] Create `rosterSearchSchema` and the roster query hook in `frontend/src/entities/trainer-context/`, keyed under `ctxKeys.players(trainerId, search)`
- [X] T252 [US6] Build `frontend/src/widgets/trainer-roster-table/`, `frontend/src/pages/trainer-players/index.tsx`, and `frontend/src/routes/_authed/trainer/players.tsx` — reusing the directory's 500 ms debounce and `replace: true` search navigation from D-04, with paging and filters pushing normal history entries

**Checkpoint**: US6 is independently demonstrable — a stranger with a link becomes a player on a
trainer's roster, and every refusal path is silent about why. SC-015, SC-019, SC-020, and SC-021
pass.

---

### Extension Phase C: User Story 7 — Several Trainers, and Switching Between Them (Priority: P2)

**Goal**: One account holds many trainers. The active one is resolved and enforced server-side, and
nothing a player or a trainer can reach crosses the boundary between them.

**Independent Test**: Associate one player with two trainers; confirm exactly one account exists,
both appear in the switcher, every view shows only the active trainer's data, and the choice
survives signing out and back in on another device.

**Depends on**: Extension Phase B — a player must be able to join one trainer before they can join
two.

#### Tests for User Story 7

- [X] T253 [P] [US7] Write `backend/tests/integration/test_join_accept.py` asserting a signed-in player joins a second trainer with no new account, that repeating the call returns `already_associated` without a second row, and that `use_count` does **not** move on the repeat (FR-082)
- [X] T254 [P] [US7] Write `backend/tests/integration/test_trainer_context.py` covering the switch, restoration of the last-used context on a fresh session, and that naming a trainer the caller is not associated with returns **404, not 403** — a 403 would confirm that trainer exists (FR-090)
- [X] T255 [P] [US7] Write `backend/tests/integration/test_trainer_isolation.py` — a two-trainer fixture walked against **every** trainer-facing route, asserting the other trainer's identifiers and names appear in no response body. Routes are discovered from the app's route table, not hand-listed, so a new endpoint cannot be added without an isolation assertion. **This test is SC-025**
- [X] T256 [P] [US7] Write `backend/tests/integration/test_context_repair.py` asserting that deactivating the active trainer moves the player to another Active association, that deactivating all of them leaves a valid zero-trainer state rather than an error, and that reactivation restores the trainer to the switcher (FR-089)
- [X] T257 [P] [US7] Write `backend/tests/integration/test_erasure_associations.py` asserting an erased player keeps every association and appears on each roster as "Deleted User" with roster counts unchanged (FR-091, SC-008), and that erasing a trainer revokes their share links
- [X] T258 [P] [US7] Write `frontend/tests/widgets/trainer-context-switcher.test.tsx` with MSW, asserting the switcher is hidden at one trainer, listed at two, and that the `ctx` query namespace is emptied before the first render after a switch

#### Implementation for User Story 7

- [X] T259 [P] [US7] Create `backend/src/app/schemas/trainer_context.py` with `TrainerContextEntry`, `TrainerContextList`, and `TrainerContextRequest`
- [X] T260 [US7] Create `backend/src/app/services/trainer_context_service.py` — the resolve-and-repair function of research R-24 (a stored context whose association is missing, inactive, or whose trainer is not Active is replaced and the correction written back), plus list and switch. Every caller goes through it; no caller trusts the column as read
- [X] T261 [US7] Add `get_trainer_context` to `backend/src/app/core/deps.py` as a FastAPI dependency, the same shape R-14 gives the role gate. **No endpoint may accept a `trainer_id` parameter to select context** (research R-25) — an endpoint that forgets the check is then merely wrong, not vulnerable
- [X] T262 [US7] Add `POST /join/{code}/accept` to `backend/src/app/api/v1/join_router.py` — associate, switch context, and refuse a non-`player_parent` role with `role_cannot_join`, writing nothing (FR-081)
- [X] T263 [US7] Add `GET /me/trainers` and `PUT /me/trainer-context` to `backend/src/app/api/v1/me_router.py`, both gated to the Player/Parent role
- [X] T264 [US7] Extend `CurrentUser` in `backend/src/app/schemas/auth.py` and its assembly in `backend/src/app/services/auth_service.py` with `active_trainer_id` and `trainer_count`, resolved through `trainer_context_service` so a stale context is repaired on the session read
- [X] T265 [US7] Extend `backend/src/app/services/erasure_service.py` with the data-model §20 delta — clear `player_name`, `date_of_birth`, and `active_trainer_user_id`; leave `gender` and every association intact; revoke the share links of an erased trainer; clear `logo_key` and remove the stored file
- [X] T266 [P] [US7] Extend the session type in `frontend/src/entities/session/` with `active_trainer_id` and `trainer_count`, and add the trainers query and switch mutation to `frontend/src/entities/trainer-context/api/`
- [X] T267 [P] [US7] Build `frontend/src/widgets/trainer-context-switcher/` — each trainer's logo and name, rendered only when `trainer_count > 1` (FR-088), with the open/closed flag as the one new `UiState` field (frontend-contracts §11)
- [X] T268 [US7] Mount the switcher in `frontend/src/widgets/app-shell/` beside the identity block, without disturbing the breadcrumb trail or back-control region D-05 established
- [X] T269 [US7] Wire the switch sequence in `frontend/src/entities/trainer-context/api/use-switch-context.ts` — await the mutation, then `queryClient.removeQueries({ queryKey: ctxKeys.root })`, **then** let the session refetch resolve. Removing after the session settles would render one frame from the previous context, which is what FR-087 forbids
- [X] T270 [P] [US7] Add the zero-trainer empty state to the player landing view in `frontend/src/pages/dashboard/index.tsx` — an account with no association is valid, not an error (research R-24)
- [X] T271 [US7] Add the `can_join` and `already_associated` branches to `frontend/src/pages/join/index.tsx` — one confirm button, and a link into the trainer's context respectively
- [X] T272 [US7] Add a test to `frontend/tests/` asserting that every query key touching trainer-scoped data begins `['ctx', trainerId]` — the convention is only worth fixing now if it is enforced now (research R-26)

**Checkpoint**: US6 and US7 both work independently. One account spans trainers, the boundary
between them holds under a route-table sweep, and SC-016, SC-017, SC-018, and SC-025 pass.

---

### Extension Phase D: User Story 8 — A Trainer Brands Their Portal (Priority: P3)

**Goal**: A trainer's logo and colour appear for them, for their players in their context, and on
their join page — and nowhere else.

**Independent Test**: As a trainer, upload a logo and set a colour; confirm a player associated with
that trainer sees both, a player in another trainer's context sees the platform default, and
`/login` is never branded.

**Depends on**: Extension Phase A. Scenario 6 of the story — branding following a context switch —
additionally needs Extension Phase C; every other scenario is testable without it.

#### Tests for User Story 8

- [X] T273 [P] [US8] Write `backend/tests/integration/test_branding.py` covering read, colour update, reset, that an omitted key leaves the colour unchanged while an explicit `null` clears it (Principle VI), and that a Coach and a Player/Parent both receive 403 (FR-093)
- [X] T274 [P] [US8] Write `backend/tests/integration/test_branding_logo.py` covering an accepted PNG, a 3 MB file refused with 413, a mislabelled `.pdf` refused with 422, a 1200×1200 PNG **fitted rather than refused** (FR-096), a hostile SVG refused, and a replaced logo's previous file becoming unreachable (FR-103)
- [X] T275 [P] [US8] Write `backend/tests/integration/test_branding_media.py` asserting `GET /media/branding/{key}` serves without a session, and that an SVG response carries `X-Content-Type-Options: nosniff` and the `default-src 'none'` content-security policy (research R-27)
- [X] T276 [P] [US8] Write `frontend/tests/widgets/branding-provider.test.tsx` asserting the provider sets the custom properties from the session's branding, falls back to the platform default when it is absent, and repaints on a context switch with no frame showing the previous trainer's identity (SC-024)

#### Implementation for User Story 8

- [X] T277 [P] [US8] Create `backend/src/app/schemas/branding.py` with `PortalBranding` and `PortalBrandingUpdate` — `primary_color` is `str | None` matching `^#[0-9a-fA-F]{6}$`, and the update model is read with `model_dump(exclude_unset=True)` so an omitted key and an explicit `null` stay distinguishable
- [X] T278 [US8] Create `backend/src/app/services/branding_service.py` with `resolve_for_viewer(user)` — a trainer resolves their own, a `player_parent` resolves the active context's, Super Admin and unauthenticated resolve the platform default, and **coach returns the default with a `TODO(US-01.08)` naming the one line that changes** when the employer link exists (research R-33). This is a known gap between FR-101 as written and what ships
- [X] T279 [US8] Add update, reset, and the logo lifecycle to `backend/src/app/services/branding_service.py` — upload validates through `image_processing` or `svg_screening` by type, stores through the existing photo storage port, and removes the previous file on replace or reset
- [X] T280 [P] [US8] Add fit-to-200×200 with preserved aspect ratio to `backend/src/app/services/image_processing.py` for raster logos. Vector logos are not resized — they scale (FR-096)
- [X] T281 [US8] Add `GET`/`PATCH /me/branding`, `PUT`/`DELETE /me/branding/logo`, and `POST /me/branding/reset` to `backend/src/app/api/v1/me_router.py`, all gated to the Trainer role
- [X] T282 [US8] Add the **unauthenticated** `GET /media/branding/{key}` to `backend/src/app/api/v1/media_router.py` with the `nosniff` and content-security-policy headers on SVG responses. This is a deliberate departure from the authenticated photo endpoint, recorded in plan.md §Complexity Tracking — FR-073 puts branding on a page reached before an account exists
- [X] T283 [US8] Wire `portal_branding` into `CurrentUser` in `backend/src/app/schemas/auth.py` and into `JoinLinkPreview` in `backend/src/app/schemas/join.py`, both through `branding_service.resolve_for_viewer` — one resolution, server-side; the client must not decide whose branding applies (frontend-contracts §14)
- [X] T284 [US8] Create `brandingSchema` and the branding form in `frontend/src/features/trainer/branding/` — colour picker with live preview, logo file input with in-place preview, and **nothing applied to anyone until save** (FR-097)
- [X] T285 [P] [US8] Build `frontend/src/widgets/branding-provider/` — reads the branding, calls `brandPalette`, and sets CSS custom properties on a wrapper element, overriding the `DESIGN_TOKENS.md` defaults. No component reads `primary_color` and no component holds a hex literal, which is what keeps the design-token rule intact under runtime theming
- [X] T286 [US8] Mount the provider in `frontend/src/routes/_authed.tsx` and in `frontend/src/routes/join.$code.tsx`, whose branding comes from the preview response rather than the session. `/login` and `/set-password` stay on the platform default (FR-101)
- [X] T287 [US8] Add the branding half to `frontend/src/pages/trainer-portal/index.tsx` beside the share-link panel from T250, with the reset control (FR-100)
- [X] T288 [P] [US8] Render every logo through `<img>` with `resolveMediaUrl` in `frontend/src/widgets/app-shell/`, `frontend/src/widgets/trainer-context-switcher/`, `frontend/src/widgets/trainer-roster-table/`, and `frontend/src/pages/join/index.tsx` — never `<object>`, `<embed>`, or inline SVG. This is the layer of R-27's defence that holds even if the server-side screening is wrong
- [X] T289 [P] [US8] Add the branded join page rendering to `frontend/src/pages/join/index.tsx` so a visitor sees the trainer's identity before entering any detail (FR-073)
- [X] T290 [US8] Verify that a branding save reaches a signed-in player and coach on their next view without a sign-out, by invalidating `branding` and `session` in the mutation's `onSuccess` in `frontend/src/features/trainer/branding/api/use-update-branding.ts` (FR-102, SC-022)

**Checkpoint**: All three extension stories work independently. SC-022, SC-023, and SC-024 pass, and
the extension is functionally complete except for the coach audience of FR-101, which is blocked on
US-01.08.

---

### Extension Phase E: Polish & Cross-Cutting Concerns

- [X] T291 Extend `backend/tests/integration/test_permission_matrix.py` to cover every route the extension adds — join, share-link, trainers, trainer-context, branding, branding media, and roster — confirming the route-table discovery in T144 picks them up automatically rather than needing them hand-listed (SC-002)
- [X] T292 Regenerate and re-run the contract test in `backend/tests/contract/test_openapi_contract.py` against `contracts/openapi.yaml` v1.1.0, failing on any drift across its 33 operations and 37 schemas
- [X] T293 [P] Add the two extension greps from quickstart.md §Quality gates to `.github/workflows/ci.yml` — no `trainer_id` arriving as a query or path parameter outside the admin router (research R-25), and no logo rendered through `<object>`, `<embed>`, or `dangerouslySetInnerHTML` (research R-27). Both must print nothing
- [X] T294 [P] Accessibility pass over the join form, the branding controls, and the context switcher — labels, focus management, keyboard operation of the switcher dropdown and the colour picker — across `frontend/src/features/join/`, `frontend/src/features/trainer/`, and `frontend/src/widgets/trainer-context-switcher/`
- [X] T295 [P] Add loading, empty, and error states across `frontend/src/pages/join/index.tsx`, `frontend/src/widgets/trainer-roster-table/`, `frontend/src/widgets/trainer-context-switcher/`, and `frontend/src/features/trainer/branding/`, including the zero-trainer and zero-player cases
- [X] T296 [P] Extend `backend/src/app/services/maintenance_service.py` to prune `link_lookup_attempts` alongside sessions and sign-in attempts
- [X] T297 Verify SC-016 and SC-018 by timing an accept-and-land and a context switch, and record the measurements in `specs/001-user-roles-admin/quickstart.md` beside the existing SC-006 measurement
- [X] T298 Run the full quality gate from quickstart.md §6 — ruff, mypy strict, pytest, ESLint including the boundaries rule, `tsc -b --noEmit`, Vitest — and fix every finding introduced by T205–T297
- [X] T299 Walk every scenario in quickstart.md US6, US7, and US8 manually and reconcile any divergence between documented and actual behaviour
- [X] T300 [P] Update `backend/README.md` and `frontend/README.md` with the join flow, the server-resolved context rule, and the `['ctx', …]` key convention that every later epic inherits

---

### Extension: Dependencies & Execution Order

```
Extension A (T205–T224)
        │
        ├──▶ Extension B / US6 (T225–T252) ──▶ Extension C / US7 (T253–T272) ──┐
        │                                                                       ├──▶ Extension E
        └──▶ Extension D / US8 (T273–T290) ─────────────────────────────────────┘      (T291–T300)
                        ▲
                        └── scenario 8.14 only (branding across a context switch) needs C
```

- **Extension A is the single entry point.** Every other task depends on the schema and the two
  primitives it creates
- **US7 depends on US6**: a player must be able to join one trainer before joining two. This is a
  genuine dependency, not a sequencing preference — `POST /join/{code}/accept` extends the router
  T239 creates, and the context switcher has nothing to switch between until associations exist
- **US8 depends only on A** for everything except scenario 8.14. A second developer can take US8 in
  parallel with US6 and US7 the moment A is done; only the context-switch branding test waits
- **Within US6**, backend precedes frontend: T245–T252 consume the endpoints T239–T243 expose
- **Extension E depends on B, C, and D**

### Extension: Same-File Serialization

Additions to the two lists above; these must not be parallelized despite sitting in different phases:

- `backend/src/app/models/role_details.py` — T208, T209
- `backend/src/app/models/enums.py` — T205 (nothing else in the extension touches it)
- `backend/src/app/api/v1/me_router.py` — T240, T263, T281
- `backend/src/app/api/v1/join_router.py` — T239, T262
- `backend/src/app/api/v1/media_router.py` — T282
- `backend/src/app/schemas/auth.py` — T264, T283
- `backend/src/app/schemas/join.py` — T233, T283
- `backend/src/app/services/share_link_service.py` — T234, T236
- `backend/src/app/services/branding_service.py` — T278, T279
- `backend/src/app/services/user_admin_service.py` — T235 (and T080, T081, T120, T121, T167 from earlier phases)
- `backend/src/app/services/erasure_service.py` — T265 (and T129–T131 from Phase 7)
- `backend/src/app/services/image_processing.py` — T280
- `backend/src/app/repositories/association_repository.py` — T214, T242
- `backend/src/app/core/deps.py` — T261
- `backend/src/app/core/config.py` — T220 (and T015, T187, T188)
- `backend/src/app/cli.py` — T244 (and T145, T146)
- `frontend/src/entities/user/api/query-keys.ts` — T223
- `frontend/src/shared/api/types.ts` — T222
- `frontend/src/pages/join/index.tsx` — T248, T271, T289
- `frontend/src/pages/trainer-portal/index.tsx` — T250, T287
- `frontend/src/pages/dashboard/index.tsx` — T270 (and T067, T203)
- `frontend/src/routes/_authed.tsx` — T286 (and T039, T202)
- `frontend/src/widgets/app-shell/` — T268 (and T200, T201)
- `frontend/src/routes/__root.tsx` — **no extension task touches this file.** Recorded so the
  omission stays deliberate: the branding provider mounts at `_authed` and at the join route, never
  at the root, because the root also carries `/login` and `/set-password`, which must show the
  platform default (FR-101)

### Extension: Parallel Example — Phase A

```bash
# The three repositories and the two pure primitives are independent files:
Task: "Create share_link_repository.py"                 # T213
Task: "Create association_repository.py"                # T214
Task: "Create link_lookup_attempt_repository.py"        # T215
Task: "Create svg_screening.py"                         # T216
Task: "Create brand-palette.ts"                         # T218

# Then their tests, also independent:
Task: "test_svg_screening.py"                           # T217
Task: "brand-palette.test.ts — the SC-023 contrast sweep"  # T219
```

### Extension: Parallel Example — User Story 6 tests

```bash
# All seven US6 test files are different files with no shared fixtures beyond conftest:
Task: "test_share_link_service.py"      # T225
Task: "test_join_preview.py"            # T226
Task: "test_join_register.py"           # T227
Task: "test_join_validation.py"         # T228
Task: "test_join_link_throttle.py"      # T229
Task: "test_trainer_roster.py"          # T230
Task: "join.test.tsx"                   # T231
```

### Extension: Implementation Strategy

**Extension MVP — US6 only**

1. Extension Phase A (T205–T224) — schema, repositories, primitives
2. Extension Phase B (T225–T252) — US6
3. **STOP and VALIDATE**: walk quickstart US6 end to end
4. Deployable: trainers can hand out a link and players can join themselves. That alone removes the
   Super Admin from the player-onboarding path, which is the extension's whole business case

**Incremental delivery**

1. A → B → demo self-service onboarding (SC-015, SC-019, SC-020, SC-021)
2. + C → demo one account across two trainers with provable isolation (SC-016 – SC-018, SC-025)
3. + D → demo a branded portal (SC-022 – SC-024)
4. + E → gates green, timings recorded

**Parallel team strategy**

With two developers, once Phase A is done: one takes B then C (they are a chain), the other takes D
in full. They meet at Phase E. D's only wait is the single context-switch branding test.

### Extension: Traceability

| Story | Spec requirements | Plan decisions | Success criteria | Tasks |
|---|---|---|---|---|
| Foundational | data-model §15–§24 | R-21, R-22, R-27, R-29, R-30, R-31, R-32 | — | T205–T224 |
| **US6** | FR-065 – FR-083 | R-21, R-22, R-23, R-30, R-31 | SC-015, SC-019, SC-020, SC-021 | T225–T252 |
| **US7** | FR-084 – FR-092 | R-24, R-25, R-26 | SC-016, SC-017, SC-018, SC-025 | T253–T272 |
| **US8** | FR-093 – FR-104 | R-27, R-28, R-29, R-33 | SC-022, SC-023, SC-024 | T273–T290 |
| Polish | SC-002, quality gates | — | SC-002 | T291–T300 |

### Extension: Open decision to raise before implementation

**FR-101's coach clause cannot ship in this slice.** A coach will see the platform default rather
than their trainer's branding, because which trainer a coach works for is US-01.08 — out of scope —
so `coach_details` has no employer column and nothing could populate one. T278 carries the branch
and the `TODO(US-01.08)`.

Everything else in User Story 8 ships complete. **If the coach audience is required now, the
coach-to-trainer link has to come into scope with it** — that is a specification decision, and it
would add tasks to Extension Phase D rather than change any task already listed. Nothing else in
this extension is blocked; implementation may begin at T205.

---

## Fixes: Navigation Entry Points

**Added**: 2026-08-27 | **Source**: post-implementation bug report against branch
`feature/share-link-and-customization`

Reported verbatim: *"None of the UIs for any role feature navigation or buttons to access new
features; in other words, they are inaccessible."*

Numbering continues from T300; **no existing task is renumbered or altered.** The defect marker
continues the F-series at **F7**.

### Format for this phase: `[ID] [P?] [Fix] Description`

| Marker | Reported defect | Verified root cause |
|---|---|---|
| **F7** | New features are unreachable by clicking — no role's interface offers navigation or a button to them | The extension built four routes (`/trainer` layout, `/trainer/portal`, `/trainer/players`, `/join/$code`) and **no task in Extension Phases B–E adds a link to any of them.** A repository-wide search for `to="/trainer` in `frontend/src/` returns only `useNavigate({ from: '/trainer/players' })` inside the roster table — no `<Link>` anywhere. `/trainer/portal` (FR-069's copy-and-regenerate panel, FR-093–FR-104's branding controls) and `/trainer/players` (FR-090's roster) are therefore reachable only by typing the URL. Compounding it: `use-breadcrumbs.ts` `ROUTE_LABELS` and the `BreadcrumbCrumb` union were never extended for the trainer routes (T200/T201 predate them), so those pages render **zero crumbs** and the shell reports neither where the person is nor a way back; and the dashboard's trainer branch is still T067's `"Welcome back."` placeholder, written before the two trainer pages existed. The gap reaches the validation walk itself — `quickstart.md` 6.5 and 8.1 instruct the tester to *open* `/trainer/players` and `/trainer/portal` by URL, which is why the walkthrough passed with no entry point in place |

**Per-role reachability, as built** (verified 2026-08-27 against `frontend/src/`):

| Role | Feature | Entry point today | Verdict |
|---|---|---|---|
| Super Admin | User directory `/admin/users` | One text link in `pages/dashboard/index.tsx` | Reachable, but from the landing page only — no header nav, so it is unreachable from every other page except through the breadcrumb trail |
| Super Admin | User detail, erasure record | Row link in `widgets/user-directory-table` | Reachable — correct as a row action |
| **Trainer** | **Invitation link (copy/regenerate) — `/trainer/portal`** | **none** | **Inaccessible.** Blocks the whole of US6: a trainer cannot obtain the link, so no player can join, so US7 and US8 cannot be demonstrated through the interface at all |
| **Trainer** | **Portal branding (logo, colour, reset) — `/trainer/portal`** | **none** | **Inaccessible** |
| **Trainer** | **Roster — `/trainer/players`** | **none** | **Inaccessible** |
| Coach | — | n/a | No dedicated page exists in this feature; `/profile` is reached from the shell. Correct, and recorded so the empty case is deliberate rather than an omission |
| Player/Parent | Trainer switcher | `widgets/app-shell`, rendered only above one trainer (FR-088) | Correct |
| Player/Parent | Active trainer identity at exactly one trainer | none — the switcher is correctly hidden and nothing replaces it | Gap against FR-062's "where in the platform they currently are": after joining, the player lands on `"Welcome back."` with no statement of whose portal they are in |
| Player/Parent | Join by link `/join/$code` | The link itself, off-platform | Correct by design — the link is printed and posted (FR-065) |

**Root cause is a task-level gap, not only a coding slip.** `plan.md` D-05 fixed the shell's contents
as identity + breadcrumbs + profile + sign-out + back region, and `contracts/frontend-contracts.md`
§7.3 records exactly that. Neither names a primary navigation region, and no requirement in `spec.md`
obliges a role's permitted features to be *reachable* — FR-019 says the landing area exposes "only
the actions their role permits", which is a restriction on what may be shown, not an obligation to
show it. So T250 and T252 could create routes, T203 could remove the dashboard's header, and every
gate could stay green with three pages orphaned. The proposed FR-105 and the D-07 decision below
close that hole; T308's orphan-route test is what keeps it closed as Epics 02–08 add routes.

---

### Fix Phase I: Role navigation entry points (F7)

**Purpose**: Every feature a role may use is reachable by clicking, from a single role-aware
descriptor list that the header and the landing area both read, so the two cannot drift.

**Depends on**: nothing outstanding — Fix Phases A–H and Extension Phases A–E are all complete.

**Execution order**: T301 → T302 → T303 → T304 → T305 → T306 → T307 → T308, then T309–T311 in
parallel, then T312.

- [x] T301 [F7] Create `frontend/src/widgets/app-shell/model/use-nav-items.ts` — a role-aware list of typed nav descriptors, a discriminated union on `to` exactly like `BreadcrumbCrumb` in `use-breadcrumbs.ts`, derived from the `session` query through `entities/session/model/role-guards`: `super_admin` → Users (`/admin/users`, carrying the directory's default search params); `trainer` → Portal settings (`/trainer/portal`) and Players (`/trainer/players`); `coach` and `player_parent` → an empty list, **deliberately** — this feature gives them no dedicated page beyond `/profile` and the switcher, and a link to a page that does not exist is worse than no link. No URL built from a string, no `any` (Principle II, Principle IV routing rule)
- [x] T302 [F7] Create `frontend/src/widgets/app-shell/ui/primary-nav.tsx` rendering T301's descriptors as TanStack Router `<Link>`s with `activeProps` marking the current section, composing `shared/ui` primitives only; render nothing at all when the list is empty rather than an empty bar. Any shadcn primitive this needs is added through the CLI into `shared/ui` and nowhere else (Principle IV). These links are a **rendering** decision, never a permission boundary — every target is guarded again by its route and again by the server (FR-015)
- [x] T303 [F7] Mount `PrimaryNav` in `frontend/src/widgets/app-shell/ui/app-shell.tsx` beside the breadcrumb region, leaving the identity block, the back-control region (D-05), and the switcher slot (T268) untouched
- [x] T304 [F7] Extend `frontend/src/widgets/app-shell/model/use-breadcrumbs.ts` — add `'/trainer/portal'` and `'/trainer/players'` members to the `BreadcrumbCrumb` union and their labels to `ROUTE_LABELS` under route ids `/_authed/trainer/portal` and `/_authed/trainer/players`. The `/_authed/trainer` layout route stays absent for the same reason `/_authed/admin` is — it renders only an `<Outlet/>` and has no page to link to. Today both trainer pages produce an empty trail, so the shell states neither where the person is nor how to get back (FR-062)
- [x] T305 [F7] Add the two matching `case` branches to `CrumbLink` in `frontend/src/widgets/app-shell/ui/app-shell.tsx` — same file as T303, so these run in sequence. The switch is exhaustive over the union, so T304 landing without this is a compile error, which is exactly the guarantee the union was chosen for
- [x] T306 [F7] Replace the trainer branch's `"Welcome back."` placeholder in `frontend/src/pages/dashboard/index.tsx` with the trainer's landing entries — Portal settings (invitation link and branding) and Players — read from T301's descriptors rather than hand-written links, so the landing area and the header can never disagree. FR-019 makes the landing area where a role's actions are exposed; T067's placeholder predates both trainer pages. Keep the `player_parent` zero-trainer empty state from T270 and the Super Admin directory link unchanged
- [x] T307 [F7] Render the active trainer's name for a `player_parent` whose `trainer_count === 1`, where FR-088 correctly forbids the switcher — a static context label in `frontend/src/widgets/trainer-context-switcher/ui/trainer-context-label.tsx`, chosen by the existing switcher component so the shell keeps one slot, reading `active_trainer_id` from the session and the name from `userKeys.trainers`. A player who has just joined otherwise lands on `"Welcome back."` with nothing naming whose portal they are in (FR-062). The switcher itself still renders only above one trainer
- [x] T308 [F7] Add the orphan-route regression gate in `frontend/tests/routes/entry-points.test.tsx` — enumerate every authenticated path from the generated route tree (`frontend/src/routeTree.gen.ts`, as T255 discovers backend routes from the app's route table rather than hand-listing them) and assert each one is reachable for at least one role from T301's descriptors or T306's landing content, with an explicit allow-list for the paths that are correctly reached another way: `/profile` (shell link), `/admin/users/$userId` (directory row action), `/trainer` (layout route, no page). A route added by Epics 02–08 with no entry point fails here. **This is the gate that stops F7 recurring**
- [x] T309 [P] [F7] Extend `frontend/tests/widgets/app-shell.test.tsx` — the nav lists Users for a Super Admin, Portal settings and Players for a Trainer, and nothing for a Coach or a Player/Parent; the active section is marked; the trail on `/trainer/portal` reads Home → Portal settings; and the identity block, back region, and switcher slot still render as T204 asserted
- [x] T310 [P] [F7] Add `frontend/tests/pages/dashboard.test.tsx` — per-role landing content: the directory link for a Super Admin, both trainer entries for a Trainer, the zero-trainer empty state for an unassociated player, and the active trainer's name for an associated one at exactly one trainer
- [x] T311 [P] [F7] Update the navigation steps in `specs/001-user-roles-admin/quickstart.md` — 6.5 and 8.1 instruct the tester to open `/trainer/players` and `/trainer/portal` by URL, which is how three orphaned pages survived a full manual walkthrough. State the click path through the header instead, and add one step to the US6 walk asserting a trainer signing in can reach their invitation link without typing a URL
- [x] T312 [F7] Run the full quality gate from quickstart.md §6 — ruff, mypy strict, pytest, ESLint including the boundaries rule, `tsc -b --noEmit`, Vitest — and fix every finding introduced by T301–T311

**Checkpoint**: A trainer signing in can reach their invitation link, their branding, and their roster
by clicking; every authenticated page carries a breadcrumb trail; a player always sees whose portal
they are in; and no route can be added without an entry point.

---

### Fixes: Navigation — Same-File Serialization

Additions to the three lists above; these must not be parallelized:

- `frontend/src/widgets/app-shell/ui/app-shell.tsx` — T303, T305 (and T201, T268)
- `frontend/src/widgets/app-shell/model/use-breadcrumbs.ts` — T304 (and T200)
- `frontend/src/widgets/app-shell/model/use-nav-items.ts` — T301 (consumed by T302 and T306, so both wait on it)
- `frontend/src/pages/dashboard/index.tsx` — T306 (and T067, T203, T270)
- `frontend/src/widgets/trainer-context-switcher/` — T307 (and T267)
- `frontend/tests/widgets/app-shell.test.tsx` — T309 (and T204)

### Fixes: Navigation — Specification approval state

**APPROVED AND APPLIED** (user approval, 2026-08-27). Tasks T301–T312 are backed by requirements
already in `spec.md` — FR-019 (the landing area exposes the role's actions), FR-061 and FR-062 (the
navigation frame states where the person is and offers a way back), and SC-014 — so nothing in this
phase contradicted an approved artifact and implementation was never blocked on the amendment below.

The amendment adds the **explicit** obligation whose absence allowed the defect, plus the contract
rows a reviewer would look for. Applied:

| Artifact | Change |
|---|---|
| `spec.md` | New **FR-105** under Presentation and navigation: every capability a role is permitted MUST be reachable by navigation or a control from that role's landing area or navigation frame, without typing a URL; and a new **SC-026** measuring it as zero orphaned views per role |
| `plan.md` | New **D-07** in Post-Implementation Technical Decisions: one role-aware typed nav descriptor list read by both the shell and the landing area; the rejected alternatives (hand-written links per page; a route-meta `nav` field) |
| `contracts/frontend-contracts.md` | §7.3 gains a **Primary nav** row; §8's route table gains a "Reached from" column naming each new route's entry point |

`data-model.md` and `contracts/openapi.yaml` need no change — this defect is entirely in the
presentation layer and adds no field, endpoint, or column.

Traceability:

| Fix | Requirements | Plan decision |
|---|---|---|
| F7 | FR-019, FR-061, FR-062, SC-014; proposed FR-105, SC-026 | proposed D-07 |

---

## Extension: Parent/Child Family Accounts & the Approval Workflow

**Added**: 2026-08-27 | **Source**: spec.md User Stories 9–13, FR-106 – FR-159, SC-027 – SC-041 |
**Design**: plan.md §Extension (2026-08-27), research.md Part D (R-34 – R-51), data-model.md §25–§35,
contracts/openapi.yaml v1.2.0, contracts/frontend-contracts.md §15–§21, quickstart.md US9–US13

Numbering continues from T312; **no existing task is renumbered or altered.**

**Unlike the two previous extensions, this one is not purely additive.** Family Phase A rewrites code
that exists and passes its tests today: `player_details` is dropped, the trainer association is
re-pointed from an account to a player profile, and the active context moves to its own table
(research R-34, R-35, R-36). data-model.md §35 enumerates what that touches — ten backend call sites,
four frontend modules, thirteen test files — and Family Phase A is that list turned into tasks. A
reviewer should expect Phase A to change many files and add **no user-visible behaviour**; its proof
is the existing suite passing against the new shape.

### Format for this phase: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependency on incomplete work
- **[Story]**: US9 – US13, matching spec.md. Family-Foundational and Family-Polish tasks carry no
  story label, because every story depends on them

| Story | Spec | Priority | Delivers |
|---|---|---|---|
| **US9** | User Story 9, FR-106 – FR-113, FR-122 – FR-123 | P1 | One account holding a whole family, with each child's trainers chosen as the profile is created |
| **US10** | User Story 10, FR-124 – FR-128 | P1 | A parent adding and removing each child's trainers, with history preserved |
| **US11** | User Story 11, FR-129 – FR-140 | P2 | A child's own sign-in that can look but not spend, commit, or reach a sibling |
| **US12** | User Story 12, FR-141 – FR-159 | P2 | The Pending Parent Approval workflow — the story this extension exists to deliver |
| **US13** | User Story 13, FR-122 (join path) | P3 | The family-member selection prompt when a parent follows a new trainer's link |

**Tests are included**, on the same reasoning as every earlier phase: the constitution makes passing
tests a merge gate, and SC-028, SC-029, SC-034, SC-038, and SC-040 each name a test as the thing that
proves them. Two of those — sibling isolation and resolve-exactly-once — cannot be demonstrated by
hand at all.

---

### Family Phase A: Foundational — the new shape (Blocking Prerequisites)

**Purpose**: Move the trainer association from the account to the player profile, add the approval
table, and rework every call site that assumed one player per account. **Delivers no new capability.**

**⚠️ CRITICAL**: No task in Family Phases B–E may begin until this phase is complete and the full
existing suite is green.

**⚠️ VERIFY T320 BEFORE PROCEEDING.** T318 re-points every trainer association in the database. No
downstream test means anything if it silently dropped rows.

- [ ] T313 Add the `PlayerProfileKind`, `ApprovalRequestKind`, and `ApprovalRequestStatus` `StrEnum`s to `backend/src/app/models/enums.py`, plus an `ALLOWED_APPROVAL_TRANSITIONS` map and `is_approval_transition_allowed()` mirroring the existing `ALLOWED_STATUS_TRANSITIONS` pattern (data-model §25). `info_requested` may not go directly to `approved` — the parent asked a question, so the answer returns the request to pending (FR-143)
- [ ] T314 [P] Create the `player_profiles` and `active_training_contexts` models in `backend/src/app/models/player_profile.py` per data-model §26 and §27 — the check constraints `ck_player_profiles_kind`, `_gender`, `_self_names`, and `_signin_is_child`; the **partial** unique index `uq_player_profiles_one_self` on `(account_user_id) WHERE kind = 'self'`; the unique index on `sign_in_user_id`; and `(account_user_id, removed_at)`. Record in a docstring that `ck_player_profiles_self_names` is what makes R-37's two name sources unambiguous
- [ ] T315 [P] Create the `approval_requests` model in `backend/src/app/models/approval.py` per data-model §28 — the check constraints `_kind`, `_status`, `_subject`, `_resolution`, and `_expiry_actor`; the **partial** unique index `uq_approval_requests_live` on `(player_profile_id, kind, trainer_user_id) WHERE status IN ('pending_parent_approval','info_requested')`; and indexes on `(parent_user_id, status)`, `(player_profile_id, status)`, and `(status, expires_at)`. `amount_minor` is an integer of minor currency units, never a float (research R-39)
- [ ] T316 Add a nullable `player_profile_id` column with its foreign key and index to `TrainerPlayerAssociation` in `backend/src/app/models/association.py`, leaving `player_user_id` in place for now (data-model §29.1). Both coexist until T319
- [ ] T317 Write Alembic revision `backend/migrations/versions/0008_create_player_profiles_and_approvals.py` creating `player_profiles`, `active_training_contexts`, and `approval_requests` with every check constraint and index from T314–T315, and adding `trainer_player_associations.player_profile_id` as **nullable** (data-model §33). Nothing is dropped and nothing is required, so the application still runs unchanged on this revision
- [ ] T318 Write Alembic revision `backend/migrations/versions/0009_migrate_players_to_profiles.py` — a **data** migration in SQLAlchemy Core against `op.get_bind()`, never raw SQL, so the two documented exceptions in plan.md §Complexity Tracking stay at two. One `player_profiles` row per `player_details` row (`kind` from `is_self`; names split from `player_name` on the **last space** for a child, `NULL` for a self player, a one-word name becoming the first name with `'—'` as the last); then `player_profile_id` backfilled on every association; then one `active_training_contexts` row per player whose `active_trainer_user_id` was set. Must be idempotent. `downgrade()` restores `player_details` **only** when every account holds exactly one profile and otherwise **raises** — a migration that silently discarded a family's second and third child is worse than one that refuses to run (research R-35)
- [ ] T319 Write Alembic revision `backend/migrations/versions/0010_finalize_profile_associations.py` — under `batch_alter_table`: make `player_profile_id` non-nullable, drop and recreate `uq_trainer_player` on `(trainer_user_id, player_profile_id)`, drop and recreate `ix_tpa_player_status` on `(player_profile_id, status)`, drop `player_user_id`; then drop the `player_details` table (data-model §29.2, §33). The unique constraint is load-bearing — it is what makes FR-082 and FR-127 caught integrity errors rather than checked preconditions
- [ ] T320 Extend `backend/tests/integration/test_migration_backfill.py` — assert the association count is identical across `0007 → 0008 → 0009 → 0010`, that every association ends with a non-null `player_profile_id`, that every account with a former context has exactly one `active_training_contexts` row, that `upgrade` run twice is a no-op, and that `0009`'s `downgrade` **raises** for an account holding two profiles. **This is the gate that makes the rest of the phase safe to build on**
- [ ] T321 [P] Create `backend/src/app/repositories/player_profile_repository.py` — insert, get by id, list live profiles for an account, get by `sign_in_user_id`, soft-remove, and a near-duplicate lookup by account plus date of birth plus case-insensitive trimmed name (data-model §32). Queries only; the duplicate *policy* belongs to the service
- [ ] T322 [P] Create `backend/src/app/repositories/approval_repository.py` — insert, get by id, list for a parent with status filter and paging, list for a player profile, list lapsed live requests for the sweep, and the **conditional resolve**: a Core `update()` whose `where` clause carries the id, the live statuses, and `expires_at > now`, returning the affected row count (research R-41). The row count is the decision — no read-then-write anywhere in this file
- [ ] T323 Rework `backend/src/app/repositories/association_repository.py` to profile granularity (data-model §35) — `get`, `insert`, `list_active_for_player`, `list_for_trainer`, and `count_for_trainer` all join on `player_profiles.id` instead of the account id, and `TrainerRosterRow` gains the profile identity, its `kind`, and the responsible account's contact detail for FR-116. Each profile's associations stay wholly independent of every other profile's on the same account (FR-115)
- [ ] T324 Rework `backend/src/app/repositories/user_repository.py` — `get_role_detail` stops returning `tuple[PlayerDetail, ParentContact | None]` for a `player_parent` and returns the parent contact alone, because the player fields are now per-profile (data-model §35); `insert_join_registration` writes a `player_profiles` row and an `active_training_contexts` row instead of a `PlayerDetail`
- [ ] T325 Rename `backend/src/app/services/trainer_context_service.py` to `training_context_service.py` and rework all three methods over `active_training_contexts` (data-model §27, research R-36) — `resolve_active_context` returns a validated `(player_profile_id, trainer_user_id)` pair, repairing a stored pair whose profile was removed, whose association is not Active, or whose trainer is not Active; `list_for_account` returns every reachable pair; `switch` validates a named pair. A signed-in child's candidate set is the single profile their sign-in is attached to, a parent's is every live profile on the account (FR-119, FR-132, research R-48). The restored pair is the one last used, falling back to another available pair or to a plain statement that the person belongs to no trainer (FR-117, FR-120)
- [ ] T326 Rework `backend/src/app/services/join_service.py` — `register` and `accept` write the context to `active_training_contexts` rather than `player_details.active_trainer_user_id`, and `register` creates a `player_profiles` row whose `kind` comes from `is_self` (data-model §35). The family-member selection and the child block are T413 and T376 — this task only moves existing behaviour onto the new shape
- [ ] T327 Rework `_anonymize_role_detail` in `backend/src/app/services/erasure_service.py` into data-model §30's transformation — every owned profile anonymized (a child's name becomes `Deleted`/`User`, not `NULL`, because the check constraint requires one and the roster must still read "Deleted User"), photos removed, `date_of_birth` cleared, `gender` and `skill_level` retained, `tokens_without_approval` cleared, contexts deleted, live approval requests expired with a null actor, and both note fields cleared. **Includes the cascade**: each child's `sign_in_user_id` account goes through the same anonymization in the same transaction
- [ ] T328 Rework `_apply_role_detail_updates` and `editable_fields_for` in `backend/src/app/services/profile_service.py` — the player fields `school`, `jersey_number`, and `skill_level` leave the account's role detail, so `player_parent` keeps only the emergency-contact fields here (data-model §35)
- [ ] T329 Update `build_role_detail_out` in `backend/src/app/schemas/role_detail.py` — `PlayerParentDetail` loses `school`, `jersey_number`, and `skill_level` and gains a read-only `profile_count`, matching `openapi.yaml` v1.2.0 (research R-34, R-49)
- [ ] T330 Create `backend/src/app/schemas/training_context.py` replacing `trainer_context.py` — `TrainingContextEntry`, `TrainingContextList`, and `TrainingContextRequest` per the contract, both halves of the pair required on the request because a trainer alone no longer identifies a context
- [ ] T331 Rework `backend/src/app/core/deps.py` — `get_training_context` and `TrainingContextDep` replace `get_trainer_context` and `TrainerContextDep`, returning the validated pair. This dependency is the **only** place an endpoint learns which profile and trainer it is scoped to; no endpoint accepts either as a path or query parameter (research R-25, R-48). The pair is the boundary every player-facing view is scoped to (FR-117). Add the `FamilyServiceDep`, `ApprovalServiceDep`, and `ChildSignInServiceDep` aliases the later phases consume
- [ ] T332 Rework `_to_current_user` in `backend/src/app/api/v1/auth_router.py` — `CurrentUser` gains `active_player_profile_id` and `is_child_account`, and `trainer_count` becomes `context_count` (contract v1.2.0). `is_child_account` is **derived** from the existence of a profile naming this account, resolved in the same statement that loads the current user rather than as a second query (research R-38)
- [ ] T333 Replace `GET /me/trainers` and `PUT /me/trainer-context` with `GET /me/contexts` and `PUT /me/context` in `backend/src/app/api/v1/me_router.py`, per the contract. No versioned duplicate is kept (research R-49). The trainer is named in the **request body**, never a path or query parameter, which is what keeps the CI guard meaningful
- [ ] T334 Reshape the roster response in `backend/src/app/api/v1/trainer_router.py` and `backend/src/app/schemas/trainer_player.py` — `TrainerPlayerSummary` names `player_profile_id` instead of `player_user_id`, carries `kind`, and carries `responsible_contact` so a trainer with a child on their roster can reach the parent (FR-116). It still reveals nothing about any other trainer **or any other profile on the same account** (FR-090, FR-116)
- [ ] T335 [P] Add the extension's domain errors and HTTP translations to `backend/src/app/core/errors.py` — `player_profile_not_found` (404), `possible_duplicate_profile` (409), `parent_only_field` (403), `child_must_ask_parent` (403), `request_already_resolved` (409), `approval_subject_unavailable` (422), `approval_kind_not_executable` (422), `approval_amount_changed` (422). The profile error carries one message whether the profile belongs to another account or to a sibling — a distinction would confirm the sibling exists (FR-112, FR-132)
- [ ] T336 [P] Update `frontend/src/shared/api/types.ts` to mirror `openapi.yaml` v1.2.0 exactly — add `PlayerProfileKind`, `PlayerProfile`, `PlayerProfileList`, `PlayerProfileAssociation`, `CreateChildProfileRequest`, `PlayerProfileUpdate`, `DuplicateProfileError`, `AddPlayerTrainerRequest`, `GrantChildSignInRequest`, `ChildSignIn`, `ApprovalRequestKind`, `ApprovalRequestStatus`, `ApprovalRequest`, `ApprovalRequestPage`, `ApprovalDecisionRequest`, `ApprovalInfoRequest`, `JoinSelectableProfile`, `JoinAcceptRequest`, `ResponsibleContact`, `TrainingContextEntry`, `TrainingContextList`, and `TrainingContextRequest`; change `TrainerPlayerSummary`, `PlayerParentDetail`, `JoinResult`, and `CurrentUser`; delete `TrainerContextEntry`, `TrainerContextList`, and `TrainerContextRequest`. Every enum a closed string union, never `string`; no `any`
- [ ] T337 [P] Widen the `ctx` namespace in `frontend/src/entities/trainer-context/api/query-keys.ts` to `ctxKeys.scope(profileId, trainerId)`, move the trainer's own roster key out to `userKeys.roster(search)`, and replace `userKeys.trainers` with `userKeys.contexts` (frontend-contracts §16, research R-47). The profile dimension is what stops one sibling's cached context data being served to the other; it is a two-line change now and a sweep across every hook after Epic-02
- [ ] T338 Rework `frontend/src/entities/trainer-context/api/` — `use-contexts.ts` replaces `use-trainers.ts` against `GET /me/contexts`, and `use-switch-context.ts` posts the pair to `PUT /me/context` and still removes the whole `ctxKeys.root` namespace before letting the session refetch settle (research R-26, R-47). Move the roster hook to read `userKeys.roster`
- [ ] T339 Regroup `frontend/src/widgets/trainer-context-switcher/ui/trainer-context-switcher.tsx` and `trainer-context-label.tsx` by profile per frontend-contracts §19 — `self` entries under "Your Training", `child` entries under "Your Children's Training", each naming the child; no heading for an empty group; **no grouping at all for a child**, whose list is flat (FR-118, FR-119). Visibility is driven by `session.context_count > 1`, exactly as `trainer_count` drove it
- [ ] T340 [P] Rework `backend/tests/helpers.py` — `create_player_with_detail` becomes `create_player_profile(db_session, *, account, kind='self', **kwargs)`, and add `create_family(db_session, *, children=2, with_sign_in=False)` returning the parent, its profiles, and any child accounts. A factory that still creates one `PlayerDetail` per account is the single biggest source of breakage in this phase
- [ ] T341 Update the backend suites that encode one player per account — `tests/integration/test_trainer_context.py`, `test_context_repair.py`, `test_trainer_roster.py`, `test_trainer_isolation.py`, the `test_join_*.py` set, `test_erasure_associations.py`, and `test_permission_matrix.py` (data-model §35). **Intent must not change**: every assertion these made about isolation, repair, and erasure must still be made, against a profile instead of an account. An assertion that becomes hard to express is a signal the rework is wrong, not that the assertion should be dropped
- [ ] T342 [P] Update the frontend tests that encode the old shape — `tests/widgets/trainer-context-switcher.test.tsx` (now grouped by profile), `tests/shared/ctx-namespace.test.ts` (the key gains a dimension), and `tests/pages/join.test.tsx`. Extend the MSW handlers in `tests/msw-handlers.ts` for `/me/contexts` and `/me/context`
- [ ] T343 [P] Update `backend/tests/contract/test_openapi_contract.py` expectations for `openapi.yaml` v1.2.0 — 51 operations, the replaced context routes gone, and the `family` and `approvals` tags present. This test is what makes R-49's "the contract and the code cannot diverge" true
- [ ] T344 Run the full quality gate from quickstart.md §6 — ruff, `mypy src` strict, pytest across unit, integration, and contract, ESLint including the boundaries rule, `tsc -b --noEmit` with zero `any`, Vitest — and fix every finding. **The gate passing with no new capability added is this phase's definition of done**

**Checkpoint**: `alembic upgrade head` reaches `0010` and leaves 16 tables; `player_details` is gone;
every trainer association names a player profile; the switcher groups by profile; and the entire
pre-existing suite passes unchanged in intent. No new endpoint answers yet beyond the two replaced
context routes.

---

### Family Phase B: US9 + US10 — Family Profiles and Their Trainers (Priority: P1) 🎯 Family MVP

**Goal**: A parent adds children, chooses which trainers each trains with as the profile is created,
and changes those associations afterwards.

**Independent test**: Sign in as a parent associated with one trainer, add two children answering yes
for one and no for the other, and confirm both profiles exist under the one account, only the first is
on the trainer's roster, and the parent's navigation offers a choice between themselves and each
child. Then add the second trainer to a child, remove it again, and confirm the roster and the history
behave as FR-126 and FR-127 require.

**Depends on**: Family Phase A complete.

- [ ] T345 [P] [US9] Create `backend/src/app/schemas/player_profile.py` — `PlayerProfile`, `PlayerProfileList`, `PlayerProfileAssociation`, `CreateChildProfileRequest`, `PlayerProfileUpdate`, `DuplicateProfileError`, and `AddPlayerTrainerRequest`, mirroring `openapi.yaml` v1.2.0. Every nullable string is `str | None` with `min_length=1`; `PlayerProfileUpdate` distinguishes an omitted key from an explicit `null` through `model_dump(exclude_unset=True)` (constitution VI). The field set is FR-107's
- [ ] T346 [P] [US9] Write `backend/tests/unit/test_family_rules.py` — the age band by kind (self ≥ 18, child 1–18, FR-108), the one-self rule, the `self`-names-must-be-absent rule (R-37), and the near-duplicate predicate: same account, same date of birth, case-insensitive trimmed name match, and **not** a fuzzy match, because siblings named for the same relative must not collide (research R-45). Covers FR-107, FR-109, and FR-110
- [ ] T347 [US9] Create `backend/src/app/services/family_service.py` — `list_profiles`, `get_profile`, `create_child`, `update_profile`, `remove_profile`. `create_child` runs the duplicate check and raises `possible_duplicate_profile` unless `acknowledge_possible_duplicate` is set, then creates the profile and associates it with exactly the trainers named in `trainer_ids`, each validated as one the account already trains with (FR-122, FR-123). An empty or omitted list creates the profile with no association. Ownership is validated in this service, never in the router (Principle III). FR-110 requires an overrulable **warning**, not a refusal, which is why the 409 carries the matches and an acknowledgement clears it
- [ ] T348 [US9] Add `GET /me/players` and `POST /me/players` to a new `backend/src/app/api/v1/family_router.py`, registered in `backend/src/app/main.py` under the `/api/v1` prefix with the `family` tag. `POST` is parent-only — a signed-in child cannot own a profile (FR-132); `GET` returns only the caller's own profile when the caller is a child (FR-132)
- [ ] T349 [US9] Add `GET`, `PATCH`, and `DELETE /me/players/{profile_id}` to `family_router.py` — same file as T348, so these run in sequence. An unreachable profile is **404, not 403**, whether it belongs to another account or to a sibling (FR-112, FR-132). `PATCH` refuses `tokens_without_approval` from a child with `parent_only_field` (FR-132, FR-147) and refuses name fields entirely on a `self` profile (R-37). `DELETE` is a soft removal that also ends any child sign-in (FR-111, FR-135)
- [ ] T350 [US9] Add `PUT /me/players/{profile_id}/photo` to `family_router.py` — same file as T348–T349, so it runs in sequence. Accepted for the owning parent on any profile and for a child on their own (FR-131), behind the existing `PhotoStorage` port with the same decode-validation, 5 MB limit, and thumbnail generation as a profile photo (FR-034, R-07). A `self` profile has no photo of its own and returns 422 (R-37)
- [ ] T351 [P] [US9] Write `backend/tests/integration/test_family_profiles.py` — quickstart Story 9 scenarios 9.1–9.13: creation, the three trainer-selection shapes, the age refusals, the duplicate 409 and its override, the account-holder distinction, the 404 for another account's profile, and the 403 for a Trainer attempting to add a child. **Includes racing two `self` profiles concurrently** to prove the partial unique index, which no manual walk can do (SC-027)
- [ ] T352 [US10] Extend `family_service.py` with `add_trainer` and `remove_trainer` — same file as T347, so these run in sequence. `add_trainer` accepts exactly one of an invitation `code`, validated under the same five-part predicate as any other use of it (FR-070), or a `trainer_id` the account already trains with; adding one already active returns the profile unchanged and writes nothing (FR-125). `remove_trainer` sets the association inactive, preserving every historical record (FR-126); re-adding later reuses the same profile (FR-127)
- [ ] T353 [US10] Add `POST /me/players/{profile_id}/trainers` and `DELETE /me/players/{profile_id}/trainers/{association_id}` to `family_router.py` — same file as T348–T350, so these run in sequence. Both are parent-only: a child changes no association, including their own (FR-128, FR-132). Removal is addressed by the **association's** identifier, not the trainer's, which is better addressing and keeps `trainer_id` out of path parameters where CI forbids it (research R-48)
- [ ] T354 [P] [US10] Write `backend/tests/integration/test_family_trainers.py` — quickstart Story 10 scenarios 10.1–10.11: both ways of adding, the 422 for sending both `code` and `trainer_id`, the no-op re-add, removal and the surviving history, the profile reuse on re-add, the last-association empty state, and the 403 for a child attempting either direction
- [ ] T355 [P] [US9] Create `frontend/src/entities/player-profile/api/query-keys.ts` with `familyKeys` and `frontend/src/entities/player-profile/api/use-players.ts` with the list and detail queries (frontend-contracts §16)
- [ ] T356 [P] [US9] Create the family mutations in `frontend/src/entities/player-profile/api/` — `use-create-child.ts`, `use-update-player.ts`, `use-remove-player.ts`, and `use-upload-player-photo.ts`, each honouring the invalidation contract in frontend-contracts §16. A removal additionally calls `removeQueries(ctxKeys.root)`, because the active pair may have been the removed profile's
- [ ] T357 [P] [US10] Create `frontend/src/entities/player-profile/api/use-player-trainers.ts` — the add and remove mutations, invalidating `familyKeys.profile(id)`, `userKeys.contexts`, and the session; removal also drops the `ctx` namespace
- [ ] T358 [P] [US9] Create `frontend/src/features/family/add-child/` — the TanStack Form with `createChildProfileSchema` (frontend-contracts §17), `validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' })` and `validators: { onDynamic }` per D-02, the payload routed through the single `normalizeEmptyToNull` helper per D-01, and the trainer question rendered in FR-122's three shapes: one yes/no naming the trainer, a checklist, or nothing at all
- [ ] T359 [US9] Add the duplicate-confirmation dialog to `frontend/src/features/family/add-child/` — same slice as T358, so it runs after. It reads the matched profiles from the mutation's **409 error state**, never from a store (frontend-contracts §18), and resubmits with `acknowledge_possible_duplicate: true`
- [ ] T360 [P] [US9] Create `frontend/src/features/family/edit-player/` with `playerProfileUpdateSchema` — name fields present only for a `child` profile, `tokens_without_approval` present only for a parent
- [ ] T361 [P] [US10] Create `frontend/src/features/family/add-trainer/` with `addPlayerTrainerSchema` — exactly one of `code` or `trainer_id`, enforced by a `.refine` on the object rather than either field, because the rule is about the pair (frontend-contracts §17)
- [ ] T362 [P] [US10] Create `frontend/src/features/family/remove-trainer/` — a confirmation dialog naming the child and the trainer and stating that upcoming reservations with that trainer will be cancelled (FR-126). The statement is required now; the cancellation itself belongs to Epic-02
- [ ] T363 [P] [US9] Create `frontend/src/widgets/family-roster-list/` — one row per profile showing name, age, the account-holder marker, and each associated trainer with its join date (FR-124), composing `shared/ui` primitives only
- [ ] T364 [US9] Create `frontend/src/pages/family/` and `frontend/src/pages/family-player/`, and the routes `frontend/src/routes/_authed/family.tsx` (layout, `player_parent` only), `family/index.tsx`, and `family/$profileId.tsx` per frontend-contracts §15. `$profileId` carries the child's trainers, their sign-in, and their token setting on one view, because FR-124 and FR-128 put all three on one view of one child
- [ ] T365 [US9] Extend `frontend/src/widgets/app-shell/model/use-nav-items.ts` — `player_parent` stops returning an empty list and yields Family plus Approvals for a parent, or Family plus Requests for a child (frontend-contracts §15). D-07 recorded the empty list as "correct rather than missing" because the feature gave them no page; this slice gives them three, and T308's orphan-route gate is what would otherwise fail
- [ ] T366 [US9] Add `'/family'`, `'/family/$profileId'`, `'/approvals'`, and `'/requests'` to the `BreadcrumbCrumb` union and `ROUTE_LABELS` in `frontend/src/widgets/app-shell/model/use-breadcrumbs.ts`, and the matching `case` branches to `CrumbLink` in `frontend/src/widgets/app-shell/ui/app-shell.tsx` — same files as T304 and T305, so these run in sequence. The switch is exhaustive, so the union landing without the branches is a compile error
- [ ] T367 [P] [US9] Write `frontend/tests/pages/family.test.tsx` — the list renders the account holder and children distinctly, the add-child form asks the trainer question in each of its three shapes, and the duplicate dialog appears on a 409 and resubmits with the acknowledgement
- [ ] T368 [P] [US10] Write `frontend/tests/features/family-trainers.test.tsx` — the add form refuses both-or-neither of `code` and `trainer_id`, and the removal dialog states the reservation consequence before confirming

**Checkpoint**: A parent can build their family and point each child at trainers, reachable by clicking
from the header. SC-027 and SC-028 are measurable.

---

### Family Phase C: US11 — A Child Signs In and Finds Most Doors Locked (Priority: P2)

**Goal**: A parent can grant a child their own sign-in; that child can look at their own training and
almost nothing else, and following a new trainer's link reaches the parent instead of enlarging the
family's commitments.

**Independent test**: Grant a child a sign-in, sign in as that child, and confirm every permitted view
works and every forbidden action is refused when submitted directly rather than through the interface.
Then, as the child, follow a third trainer's link and confirm no association is created and the parent
receives the email.

**Depends on**: Family Phase B complete — a child needs a profile and trainers before a sign-in means
anything.

- [ ] T369 [P] [US11] Create `backend/src/app/schemas/child_signin.py` — `GrantChildSignInRequest` and `ChildSignIn`, mirroring the contract. `invitation_sent` is a real field, not always true: a failed delivery is never reported as success (FR-064)
- [ ] T370 [US11] Create `backend/src/app/services/child_signin_service.py` — `grant` creates a `player_parent` account holding the parent-supplied email, links it as `player_profiles.sign_in_user_id`, seeds the child's mandatory `user_profiles` row from the profile per data-model §26.1, and issues a setup invitation through the existing flow (FR-025 – FR-027, FR-129). The email is subject to the platform-wide uniqueness rule, so the parent's own address is refused rather than shared (FR-004). `revoke` clears the link and revokes every session that account holds (FR-134)
- [ ] T371 [US11] Extend `update_profile` in `backend/src/app/services/family_service.py` so a parent's edit of a child's name writes **both** `player_profiles` and that child's `user_profiles` row in one transaction — same file as T347 and T352, so this runs in sequence. data-model §26.1 makes the profile authoritative and gives the copy exactly one writer; this task is that writer, and nothing else in the codebase may write a child account's `user_profiles` names
- [ ] T372 [US11] Add `PUT` and `DELETE /me/players/{profile_id}/sign-in` to `family_router.py` — same file as T348–T350 and T353, so these run in sequence. Parent-only, and only for a `child` profile: a `self` profile's sign-in is the account itself (R-37). A duplicate email is 409 `email_already_registered` (FR-129)
- [ ] T373 [US11] Add the child permission gate to `backend/src/app/core/deps.py` — same file as T331, so it runs after. A `require_parent` dependency refuses a caller whose account is a child sign-in, recording a `permission_denied` audit entry exactly as `require_roles` does (FR-020, FR-133). Every action FR-132 forbids is refused **on the request**, never only by withholding a control (FR-133)
- [ ] T374 [US11] Suspend a child's access while the parent is not Active — in `backend/src/app/services/auth_service.py`, refuse a sign-in and fail session authentication when the account is a child whose owning parent's status is not Active, and revoke child sessions in the same transaction as a parent's status change in `user_admin_service.py` and `erasure_service.py`. **Derived from the parent's status, never copied onto the child's row**, so reactivation restores access with no separate step (FR-136, research R-50)
- [ ] T375 [US11] End a child's sign-in when their profile is removed — extend `remove_profile` in `backend/src/app/services/family_service.py` (same file as T347, T352, and T371, so it runs in sequence) to clear `sign_in_user_id` and revoke that account's sessions. A credential must never outlive the player it belongs to (FR-135)
- [ ] T376 [US11] Block a signed-in child in `backend/src/app/services/join_service.py` — same file as T326, so this runs after. `accept` refuses a child with `child_must_ask_parent`, creating no association and changing nothing about their account (FR-137); `_viewer_state` returns `child_must_ask_parent` from the preview so the join page can explain before the child submits. Raising the request and emailing the parent is T377
- [ ] T377 [US11] Raise the join request and notify the parent — extend `join_service.py` (same file as T326 and T376, so it runs after both) to create an `approval_requests` row of kind `join_trainer` naming the trainer and the link, and send the parent an email naming the child and the trainer and carrying the link and a review action (FR-138). A second attempt for the same child and trainer raises **no** second request and sends **no** second email — the partial unique index makes the first true and the caught integrity error makes the second (FR-139, research R-40, R-51). A child following the link of a trainer they already train with is simply told so, with no request and no email (FR-140)
- [ ] T378 [P] [US11] Add `render_child_join_request_email` to `backend/src/app/services/templates/` — subject naming the child and the trainer, body carrying the link and a review action, addressed to the **parent's** address (FR-130, FR-138)
- [ ] T379 [P] [US11] Write `backend/tests/integration/test_child_signin.py` — quickstart Story 11 scenarios 11.1–11.3 and 11.15–11.18: granting with a fresh email, the 409 for the parent's own address, the setup-link flow through to a working child session, revocation ending sessions while leaving the profile intact, the parent's deactivation suspending the child and reactivation restoring them, and a removed profile ending the sign-in
- [ ] T380 [P] [US11] Write `backend/tests/integration/test_child_permissions.py` — every action FR-132 forbids, submitted **directly** rather than through the interface: owning a profile, changing any association, adding or removing a payment method, purchasing tokens, completing a purchase without approval, deleting the account, reading the parent's or a sibling's data, and changing `tokens_without_approval`. **This test is SC-029**
- [ ] T381 [P] [US11] Write `backend/tests/integration/test_sibling_isolation.py` — sweep every context-scoped route with a two-child fixture and assert no response body carries a sibling's data, and that naming a sibling's profile returns 404 rather than 403. **This test is SC-028 and SC-040**, and it is a different failure from the permission matrix and from the existing cross-trainer sweep: "a role cannot reach an action" and "another profile's data never appears in a response" are not the same assertion
- [ ] T382 [P] [US11] Write `backend/tests/integration/test_child_join_block.py` — quickstart Story 11 scenarios 11.9–11.14: no association created, the parent emailed exactly once however many times the child repeats it, exactly one pending request, and the already-connected case raising nothing. Covers SC-030
- [ ] T383 [P] [US11] Extend `backend/tests/integration/test_trainer_isolation.py` with a family fixture — a trainer associated with one child sees that child and the responsible parent's contact detail, and **no** sibling on the same account who does not train with them (FR-116, SC-040)
- [ ] T384 [P] [US11] Create `frontend/src/features/family/grant-sign-in/` with `grantChildSignInSchema` — refuses the signed-in account's own address client-side too, so the common mistake is caught before a round trip, and surfaces `invitation_sent: false` rather than reporting success unconditionally (FR-064, the lesson of D-06)
- [ ] T385 [US11] Add the child's constrained views — extend `frontend/src/pages/family/` (same slice as T364, so it runs after) so a child sees only their own profile, and hide the controls FR-132 forbids while relying on the server as the actual barrier (FR-133). Add the revoke control to `frontend/src/pages/family-player/`
- [ ] T386 [US11] Add the blocked-child branch to `frontend/src/pages/join/` — the `child_must_ask_parent` viewer state renders "Ask your parent to register you with this trainer" and states that the parent has been emailed (FR-137). The viewer-state union gains a fifth member and the switch stays exhaustive
- [ ] T387 [P] [US11] Write `frontend/tests/pages/join-child-block.test.tsx` and extend `frontend/tests/pages/family.test.tsx` — the child's view shows one profile and no parent-only control, and the join page renders the blocked branch

**Checkpoint**: A child can sign in, see their own training, and reach nothing else — proved by
SC-029's and SC-028's sweeps rather than by inspection. A blocked link reaches the parent.

---

### Family Phase D: US12 — A Parent Approves or Denies What Their Child Asks For (Priority: P2)

**Goal**: The Pending Parent Approval workflow, end to end and demonstrable, driven by the
join-a-trainer requests Phase C now raises.

**Independent test**: As a child, follow a new trainer's link to raise a request. As the parent, find
it in the pending list and approve it — confirm the child is associated and sees the status change.
Repeat with a denial, and a third time letting the clock pass 48 hours, confirming the request expires
as denied and the child is never associated.

**Depends on**: Family Phase C complete — a request needs an author and a subject.

**Note**: no migration here. `approval_requests` was created in Family Phase A alongside the rest of
the schema, for the same reason Phase 1 carried four revisions and Phase 7 carried three.

- [ ] T388 [P] [US12] Create `backend/src/app/schemas/approval.py` — `ApprovalRequest`, `ApprovalRequestPage`, `ApprovalDecisionRequest`, and `ApprovalInfoRequest`, mirroring the contract. `ApprovalDecisionRequest.note` is optional and `ApprovalInfoRequest.note` is required; both are `str | None` with `min_length=1` where nullable, so a note box opened and left blank sends `null` rather than `''` (constitution VI)
- [ ] T389 [P] [US12] Write `backend/tests/unit/test_approval_rules.py` — the full rule matrix: USD always requires approval under every state of `tokens_without_approval` (FR-145); a token spend requires approval when the setting is off and not when it is on (FR-146); the setting is read only at **creation**, so changing it never affects a pending request (FR-147); and every permitted and forbidden status transition from data-model §25, including that `info_requested` cannot go straight to `approved` (FR-143). **This test is SC-035, SC-036, and SC-037**
- [ ] T390 [US12] Create `backend/src/app/services/approval_executors.py` — an `ApprovalExecutor` `Protocol` carrying the `kind` it handles and a method performing the action, plus a registry and one registered implementation for `join_trainer` that creates the association exactly as a parent adding a trainer would. The two financial kinds are **deliberately unregistered**; a stub that "succeeded" would be the first test asserting money moved when it did not (research R-42, R-46)
- [ ] T391 [US12] Create `backend/src/app/services/approval_service.py` — `create` (consulting FR-145 and FR-146 to decide whether approval is needed at all, and writing `expires_at` once as `requested_at + 48 hours`), `list_for_parent`, `list_raised_by`, `resolve`, `respond`, and `withdraw`. Resolution goes through the repository's **conditional update**: one row affected means this caller decided it, zero means it was already resolved, withdrawn, or lapsed (research R-41). The predicate also carries the parent's Active status, so FR-157 needs no separate check. No action is carried out while the status is anything but `approved`, and then exactly once (FR-144)
- [ ] T392 [US12] Add the execution path to `resolve` in `backend/src/app/services/approval_service.py` — same file as T391, so it runs after. An approval resolves the executor for the request's kind and calls it **inside the same transaction** as the status change; a domain error rolls both back, so the request is left live and the parent is told why (FR-151, research R-42). An unregistered kind raises `approval_kind_not_executable` (FR-142, R-46), and an amount that no longer matches what the parent was shown raises `approval_amount_changed` rather than charging the new figure (FR-152)
- [ ] T393 [US12] Add `expire_lapsed_approval_requests` to `backend/src/app/services/maintenance_service.py` — set every live request past `expires_at` to `expired` with `resolved_at` set and `resolved_by_user_id` **null**, the one resolution with no actor, and notify both the parent and the child (FR-155, research R-43). The sweep notifies; R-41's predicate is what already makes a lapsed request unapprovable, and neither substitutes for the other
- [ ] T394 [US12] Wire the sweep into `backend/src/app/cli.py` — add it to the existing `prune` subcommand and widen that subcommand's help text to name approval expiry alongside session and attempt pruning. A command whose description omits half its effects is how an operator ends up not scheduling it (research R-43)
- [ ] T395 [P] [US12] Add the approval email templates to `backend/src/app/services/templates/` — a request raised (naming the child, what is asked, and the amount when financial), a decision taken (carrying the parent's note), an expiry (to both parties), and an informational token-spend notice that asks for no decision. All addressed to the **parent**, except the child's own status notices (FR-130, FR-148, FR-155, R-51)
- [ ] T396 [US12] Add the audit entries for approval decisions — extend the action vocabulary in `backend/src/app/repositories/audit_repository.py` and write an entry from `approval_service` for every resolution including expiry, naming the child profile, the request, the decision, the actor, any note, and the time (FR-158). Append-only, through the existing insert-only repository and its triggers (FR-055)
- [ ] T397 [US12] Create `backend/src/app/api/v1/approvals_router.py` with `GET /me/approvals`, `GET /me/approvals/{request_id}`, and the three decision endpoints `approve`, `deny`, and `request-info`, registered in `main.py` with the `approvals` tag. Parent-only; a request belonging to another account's child is 404. The queue defaults to the live statuses because it is a decision queue, not a history (FR-149). Each of the three responses may carry a note (FR-150)
- [ ] T398 [US12] Add `GET /me/requests`, `POST /me/requests/{request_id}/withdraw`, and `POST /me/requests/{request_id}/respond` to `approvals_router.py` — same file as T397, so these run in sequence. Only the child a request concerns may withdraw or respond; a child attempting to approve their own request is refused (FR-154, FR-156). The child sees every status and the parent's note on a denial or an information request (FR-153)
- [ ] T399 [P] [US12] Write `backend/tests/integration/test_approval_workflow.py` — quickstart scenarios 12.1–12.12 and 12.18: the request created and having no effect, the parent notified by both channels, approval creating the association and the child seeing it, denial with a note, the information exchange leaving `expires_at` untouched, withdrawal, the child refused approval of their own request, the direct bypass refused, and the audit entry for each decision. Also asserts the parent is notified within a minute and that an approved join reaches the trainer's roster within five seconds (SC-032, SC-033)
- [ ] T400 [P] [US12] Write `backend/tests/integration/test_approval_concurrency.py` — race two approvals of one request and assert exactly one 200, one 409, and one association; race an approval against the expiry deadline and assert the action happens either fully or not at all. **This test is SC-038**, and it cannot be walked by hand
- [ ] T401 [P] [US12] Write `backend/tests/integration/test_approval_duplicates.py` — race two creations of the same child-and-trainer request and assert exactly one exists, proving the partial unique index rather than a service check (FR-139, research R-40)
- [ ] T402 [P] [US12] Write `backend/tests/integration/test_approval_rollback.py` — revoke the trainer's link while a request waits, then approve: assert 422 `approval_subject_unavailable`, the status still **live**, and no association. Then assert a financial kind returns `approval_kind_not_executable` (FR-151, FR-142)
- [ ] T403 [P] [US12] Write `backend/tests/integration/test_approval_expiry.py` against an **injected clock** — a request past 48 hours is unapprovable before the sweep runs (the predicate) and `expired` with both parties notified after it (the sweep). Assert the information exchange does not restart the deadline. **This test is SC-034**; do not wait two days
- [ ] T404 [P] [US12] Write `backend/tests/integration/test_approval_parent_inactive.py` — a deactivated parent's pending requests cannot be resolved by anyone, are never auto-approved, and still expire on their original schedule (FR-157, SC-041)
- [ ] T405 [P] [US12] Create `frontend/src/entities/approval/api/query-keys.ts` with `approvalKeys` and `frontend/src/entities/approval/model/approval-search.ts` with `approvalSearchSchema` (frontend-contracts §16, §17)
- [ ] T406 [P] [US12] Create the approval queries and mutations in `frontend/src/entities/approval/api/` — `use-approvals.ts`, `use-raised-requests.ts`, `use-resolve-approval.ts`, `use-withdraw-request.ts`, and `use-respond-to-request.ts`. An **approval** invalidates `userKeys.contexts`, the session, and `familyKeys.profiles` as well as `approvalKeys.all`, because it created an association; a denial invalidates only the request (frontend-contracts §16)
- [ ] T407 [P] [US12] Create `frontend/src/features/approvals/decide/` with `approvalDecisionSchema` and `approvalInfoSchema` — approve, deny, and request-info controls, each able to carry a note, with the payload routed through `normalizeEmptyToNull` so an opened-but-empty note box sends `null` (frontend-contracts §17)
- [ ] T408 [US12] Handle the 409 in `frontend/src/features/approvals/decide/` — same slice as T407, so it runs after. `request_already_resolved` is an **ordinary outcome**, not an error state: the interface refreshes the queue and says the request was already decided, because a client whose own countdown still shows time remaining can legitimately lose the race (frontend-contracts §18, research R-41)
- [ ] T409 [US12] Create `frontend/src/pages/approvals/` and `frontend/src/pages/requests/` and the routes `frontend/src/routes/_authed/approvals.tsx` and `frontend/src/routes/_authed/requests.tsx` per frontend-contracts §15. The time remaining is **derived at render** from `expires_at`, never ticked in a store and never treated as authoritative (frontend-contracts §18)
- [ ] T410 [US12] Add the pending count to the navigation frame — extend `frontend/src/widgets/app-shell/model/use-nav-items.ts` (same file as T365, so it runs after) so the Approvals entry carries a count while any request is pending, which is what makes the workflow reachable by clicking (FR-159, FR-105)
- [ ] T411 [P] [US12] Write `frontend/tests/pages/approvals.test.tsx` — the queue shows child, subject, amount, and time remaining; approve, deny, and request-info each work and each can carry a note; a 409 refreshes rather than showing an error; and the derived countdown does not disable the controls
- [ ] T412 [P] [US12] Write `frontend/tests/pages/requests.test.tsx` — a child sees their own requests and their statuses, the parent's note on a denial, and can withdraw a pending one

**Checkpoint**: The whole Pending Parent Approval workflow runs end to end on join requests.
SC-031 – SC-039 and SC-041 are measurable.

---

### Family Phase E: US13 & Polish — Cross-Cutting Concerns (Priority: P3)

**Goal**: The family-member selection prompt, then the sweeps and gates that hold the whole extension
together.

**Depends on**: Family Phases B–D complete.

- [ ] T413 [US13] Add the family-member selection to `backend/src/app/services/join_service.py` — same file as T326, T376, and T377, so this runs after all three. `preview` returns `choose_family_members` with `selectable_profiles` when the caller is a parent holding at least one child, each flagged `already_associated` (FR-122, Story 13); `accept` associates exactly the profiles named, ignoring those already connected so the link's use count rises by the number of **new** associations only (FR-068, FR-082). Selecting nobody associates nobody and changes nothing. An account holding exactly one profile may send no body, preserving the 1.1.0 behaviour
- [ ] T414 [US13] Add `JoinSelectableProfile` and `JoinAcceptRequest` to `backend/src/app/schemas/join.py`, and set the active context after a multi-profile join to the account holder's profile when it was selected and otherwise the first selected child (Story 13 scenario 6)
- [ ] T415 [P] [US13] Write `backend/tests/integration/test_join_family_selection.py` — quickstart Story 13 scenarios 13.1–13.9: the question offered only when children exist, exactly the selected profiles associated, the use count rising by exactly the number of new associations, the empty selection changing nothing, the no-children case unchanged from US7, already-connected profiles unselectable and free, and the resulting active context
- [ ] T416 [P] [US13] Create the family-member picker in `frontend/src/features/join/accept/` with `joinAcceptSchema` — the selection lives in the form, not a store (frontend-contracts §18); already-associated profiles render as connected and unselectable; an empty selection is a valid submission
- [ ] T417 [US13] Add the `choose_family_members` branch to `frontend/src/pages/join/` — same page as T386, so it runs after. The viewer-state union gains its sixth member and the switch stays exhaustive
- [ ] T418 [P] [US13] Write `frontend/tests/pages/join-family-selection.test.tsx` — the picker lists the account holder and every child, marks the already-connected ones, and submits an empty selection without error
- [ ] T419 [P] Extend `backend/tests/integration/test_permission_matrix.py` with every route this extension adds — each of the 20 new operations against all four roles **and** against a child account, which is a fifth caller shape the matrix has never had (SC-002, FR-133)
- [ ] T420 [P] Write `backend/tests/integration/test_erasure_family.py` — erasing a parent anonymizes every owned profile, cascades to each child's sign-in account, expires live requests with a null actor, clears both note fields, leaves every association intact, and leaves participant counts and revenue sums numerically identical (data-model §30, FR-047, SC-008)
- [ ] T421 [P] Extend `frontend/tests/routes/entry-points.test.tsx` — the four new authenticated paths are each reachable by clicking for at least one role, with no new allow-list entry. A route added with no entry point fails here, which is the gate D-07 put in place (SC-026, FR-105)
- [ ] T422 [P] Add the family grep gate to `quickstart.md` §Quality gates — family accounts and to CI in `.github/workflows/` — `grep -rn "player_profile_id" backend/src/app/api/ | grep "Query("` must be empty. Ownership is validated in the service against the caller, never selected by the caller (research R-48). The existing `trainer_id` guard stays exactly as it is; this extension is the reason it matters more, not less
- [ ] T423 [P] Add an `isChildAccount` predicate to `frontend/src/entities/session/model/role-guards.ts` reading the derived session field, and use it wherever a parent-only control is rendered. A predicate, never an inline `session.is_child_account &&`, so the rule has one home
- [ ] T424 Run the full quality gate from quickstart.md §6 — ruff, `mypy src` strict, pytest across unit, integration, and contract, ESLint including the boundaries rule, `tsc -b --noEmit` with zero `any`, Vitest — plus all four greps, and fix every finding introduced by T313–T423
- [ ] T425 [P] Apply the PATCH amendment to `.specify/memory/constitution.md` removing the stale `TODO(NULL_NORMALIZATION_HELPER)` — `frontend/src/shared/lib/normalize-payload.ts` exists, is the single normalizer, and is covered by `frontend/tests/shared/normalize-payload.test.ts`; D-01 delivered it and the bug-fix slice recorded it as discharged, but the constitution's own text was never updated. Bump to **1.1.1** and record the correction in the sync-impact comment. Leaving the TODO in place teaches the next reader that Principle VI is unimplemented
- [ ] T426 [P] Add `seed-demo-family` to `backend/src/app/cli.py` — same file as T394, so it runs after. Creates a parent with a `self` profile, two children (one with a sign-in, one without), and one pending `join_trainer` request, printing the parent's and the child's credentials and the profile ids (data-model §34). The quickstart's US9–US12 walks need a family with a pending request, and building one by hand means signing in as a child, following a link, and signing back in as the parent before any assertion can be made
- [ ] T427 Walk quickstart.md's US9–US13 tables by hand against a running server and record any divergence as a new task rather than a silent fix — 72 scenarios across five stories. The two things this catches that no test does: that `prune` actually delivers both expiry emails, and that every new page is reachable without typing a URL

**Checkpoint**: The extension is complete. Every one of FR-106 – FR-159 has an implementing task, and
SC-027 – SC-041 are each measured by a named test or a walked scenario.

---

### Family: Dependencies & Execution Order

**Phase order is strict**: A → B → C → D → E. Unlike the 2026-08-26 extension, whose stories were
largely independent, these form a chain:

- **A** blocks everything. It re-points a foreign key that ten backend call sites read.
- **B** needs A — a profile must exist before it can be managed.
- **C** needs B — a child needs a profile and trainers before a sign-in means anything.
- **D** needs C — a request needs an author and a subject, which are the child and the blocked link.
- **E** needs B, C, and D — the picker touches the join path C changed, and the sweeps cover all of it.

**Within Phase A** the order is: T313 → T314–T315 (parallel) → T316 → T317 → T318 → T319 →
**T320 (verify)** → T321–T322 (parallel) → T323 → T324 → T325 → T326 → T327 → T328 → T329 → T330 →
T331 → T332 → T333 → T334 → T335 → T336–T337 (parallel) → T338 → T339 → T340 → T341 → T342–T343
(parallel) → T344.

**Do not proceed past T320 on a red result.** Everything after it assumes the association table was
migrated without loss.

### Family: Same-File Serialization

Additions to the existing lists; these must not be parallelized:

- `backend/src/app/models/enums.py` — T313 (and T205)
- `backend/src/app/models/association.py` — T316 (and T207)
- `backend/src/app/services/family_service.py` — T347, T352, T371, T375 **in that order**
- `backend/src/app/services/join_service.py` — T326, T376, T377, T413 **in that order** (and T236–T238)
- `backend/src/app/services/approval_service.py` — T391, T392 in that order
- `backend/src/app/api/v1/family_router.py` — T348, T349, T350, T353, T372 **in that order**
- `backend/src/app/api/v1/approvals_router.py` — T397, T398 in that order
- `backend/src/app/core/deps.py` — T331, T373 in that order (and T226, T264)
- `backend/src/app/cli.py` — T394, T426 in that order
- `backend/src/app/api/v1/me_router.py` — T333 (and T230, T265, T280)
- `backend/src/app/services/erasure_service.py` — T327, T374 in that order
- `frontend/src/widgets/app-shell/model/use-nav-items.ts` — T365, T410 in that order (and T301)
- `frontend/src/widgets/app-shell/model/use-breadcrumbs.ts` — T366 (and T200, T304)
- `frontend/src/widgets/app-shell/ui/app-shell.tsx` — T366 (and T201, T268, T303, T305)
- `frontend/src/widgets/trainer-context-switcher/` — T339 (and T267, T307)
- `frontend/src/pages/join/` — T386, T417 in that order (and T247)
- `frontend/src/pages/family/` — T364, T385 in that order
- `frontend/src/features/family/add-child/` — T358, T359 in that order
- `frontend/src/features/approvals/decide/` — T407, T408 in that order
- `frontend/src/shared/api/types.ts` — T336 (and T222)
- `frontend/src/entities/trainer-context/api/query-keys.ts` — T337 (and T223)
- `frontend/tests/pages/family.test.tsx` — T367, T387 in that order

### Family: Parallel Example — Phase A, after the migration is verified

```bash
# The two new repositories are independent files:
T321  backend/src/app/repositories/player_profile_repository.py
T322  backend/src/app/repositories/approval_repository.py

# And the two frontend foundational files touch nothing the backend rework touches:
T336  frontend/src/shared/api/types.ts
T337  frontend/src/entities/trainer-context/api/query-keys.ts
```

### Family: Parallel Example — Phase D tests

```bash
# All six approval test files are independent, sharing only conftest fixtures:
T399  backend/tests/integration/test_approval_workflow.py
T400  backend/tests/integration/test_approval_concurrency.py     # SC-038
T401  backend/tests/integration/test_approval_duplicates.py
T402  backend/tests/integration/test_approval_rollback.py
T403  backend/tests/integration/test_approval_expiry.py          # SC-034
T404  backend/tests/integration/test_approval_parent_inactive.py
```

### Family: Implementation Strategy

**Family MVP = Family Phase A + Family Phase B.** That delivers one account holding a family with each
child pointed at trainers — US9 and US10, both P1 — and is independently demonstrable. Phase A alone is
not a deliverable: it changes the shape and adds no capability, so shipping it on its own would be a
migration with nothing to show for it.

**The headline workflow needs Phases C and D.** US12 is what this extension exists for, and it cannot
be demonstrated without a child able to sign in and raise a request. If the slice has to be cut, cut
Phase E — US13 is a convenience, since a parent can reach the same outcome through Phase B's family
page — never Phase C or D.

**Phase A will look alarming in review.** Expect many changed files, no new behaviour, and a diff
dominated by tests being updated. The correct review question is not "what does this add" but "does
every assertion the old tests made still get made". T341 exists to make that answerable.

### Family: Traceability

| Story | Requirements | Success criteria | Key tests |
|---|---|---|---|
| Foundation | FR-114 – FR-121 | — | T320 (migration), T344 (regression gate) |
| US9 | FR-106 – FR-113, FR-122, FR-123 | SC-027 | T346, T351 |
| US10 | FR-124 – FR-128 | SC-028 | T354 |
| US11 | FR-129 – FR-140 | SC-029, SC-030 | T380, T381, T382 |
| US12 | FR-141 – FR-159 | SC-031 – SC-039, SC-041 | T389, T399 – T404 |
| US13 | FR-122 (join path), FR-068, FR-082 | SC-019 (re-checked) | T415 |
| Cross-cutting | FR-116, FR-133, FR-047 | SC-002, SC-008, SC-026, SC-040 | T419, T420, T421 |

### Family: Open decisions to raise before implementation

Carried from plan.md §Open dependencies. None blocks Phase A, but the first blocks Phase B.

1. **T318's `player_name` split heuristic needs a decision against real data** — split on the last
   space, with a one-word name becoming the first name and `'—'` the last. Acceptable for a migration,
   but only a database with real families can confirm it. If it is not acceptable, the fix is to prompt
   for the split rather than guess, which is a task, not a redesign.
2. **`prune` must be scheduled at deployment** (T394). Hourly is sufficient. Not testable, which is
   why it is written down: the correctness guarantee does not depend on it, only the notification.
3. **FR-142's financial kinds cannot be closed here** (T390). If a working purchase approval is
   required now, Epic-02's events and Epic-05's payments must come into scope with it — a spec
   decision, not a plan one. The registry means that decision costs two executor registrations.
