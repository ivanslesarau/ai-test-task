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
