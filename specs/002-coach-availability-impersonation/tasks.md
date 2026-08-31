---

description: "Task list for feature 002-coach-availability-impersonation"
---

# Tasks: Coach Invitations, Availability ("My Times") & Super Admin Impersonation

**Input**: Design documents from `/specs/002-coach-availability-impersonation/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml),
[contracts/frontend-contracts.md](./contracts/frontend-contracts.md), [quickstart.md](./quickstart.md)

**Tests**: **Included, and non-optional.** The constitution's Development Workflow gate requires that
"tests covering the acceptance criteria of the implemented tasks pass", and separately requires, for
every endpoint accepting a nullable field, one test sending an explicit `null` and one omitting the
key. Test tasks below are therefore first-class, written before the implementation they cover.

**Organization**: grouped by the seven user stories of `spec.md`, in priority order (P1 → P3), so each
story is independently implementable, testable, and demonstrable.

**Task ID numbering**: continues from feature 001, whose last task is `T427`, starting at **T500** so
that every task id is unique across this repository and the round number marks the feature boundary.
Ids run T500 – T668.

**Phase mapping to plan.md**: plan.md describes implementation phases 16 – 21; this file expands them
into one phase per user story. Plan phase 16 = Phases 1 – 2 here; 17 = Phase 3; 18 = Phase 4;
19 = Phases 5 – 6; 20 = Phase 7; 21 = Phases 8 – 9.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: which user story the task serves (US1 … US7); absent for Setup, Foundational, Polish
- Every task names its exact file path

## Path Conventions

Web application, two projects, exactly as feature 001 established:

- Backend: `backend/src/app/{api/v1,core,db,models,repositories,schemas,services}`,
  `backend/migrations/versions`, `backend/tests/{unit,integration,contract}`
- Frontend: `frontend/src/{app,entities,features,pages,routes,shared,widgets}`, `frontend/tests`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: configuration, constants, and the error vocabulary every later phase raises. No behaviour
yet.

- [x] T500 Add `coach_invitation_ttl_days: int` and `impersonation_max_minutes: int` to `Settings` in `backend/src/app/core/config.py` — required fields with no defaults, per research.md R2-21
- [x] T501 [P] Add `COACH_INVITATION_TTL_DAYS=7` and `IMPERSONATION_MAX_MINUTES=60` to `backend/.env.example` with a one-line comment each naming FR-002 and FR-046
- [x] T502 [P] Create `backend/src/app/core/availability_rules.py` with `MINUTES_PER_SLOT_STEP = 15`, `MAX_SLOTS_PER_DAY = 6`, `DAYS_IN_WEEK = 7`, `MINUTES_IN_DAY = 1440`, following `core/family_rules.py`'s shape (research.md R2-21)
- [x] T503 Add six domain errors to `backend/src/app/core/errors.py`: `CoachInvitationPending`, `InvitationNotResendable`, `CoachAddressMismatch`, `RoleCannotAccept`, `CoachAlreadyAssigned`, `ImpersonationNotPermitted` — each subclassing `DomainError` with the stable code from contracts/openapi.yaml
- [x] T504 Register the six exception handlers in `backend/src/app/main.py`, mapping to 409 / 422 / 403 / 403 / 409 / 422 respectively, each returning the single `Error` envelope; `CoachInvitationPending`'s handler adds the `invitation` key the `CoachInvitationConflict` schema requires

**Checkpoint**: `uv run pytest -q` still green; `uv run mypy src` clean; app starts only when both new env keys are present.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the schema. Everything in Phases 3 – 9 reads or writes these tables.

**⚠️ CRITICAL**: no user story work can begin until T516 passes.

- [x] T505 Add `CoachInvitationState`, `ALLOWED_COACH_INVITATION_TRANSITIONS` + `is_coach_invitation_transition_allowed`, `CoachInvitationBlockReason`, and `ImpersonationEndReason` to `backend/src/app/models/enums.py`; **remove** `ShareLinkKind.COACH_SINGLE_USE` and rewrite that enum's docstring to record that coach invitations live in their own table (data-model.md §109, research.md R2-01)
- [x] T506 [P] Create `backend/src/app/models/coach_invitation.py` — the `CoachInvitation` model with all 16 columns, five CHECK constraints, and three indexes of data-model.md §101
- [x] T507 [P] Create `backend/src/app/models/availability.py` — the `AvailabilitySlot` model with the exactly-one-owner CHECK and the four single-row CHECKs of data-model.md §103
- [x] T508 [P] Create `backend/src/app/models/impersonation.py` — the `ImpersonationSession` model with the five CHECK constraints and three indexes of data-model.md §105, docstringed with why `auth_session_id` carries no foreign key
- [x] T509 Extend `CoachDetail` in `backend/src/app/models/role_details.py` with `trainer_user_id`, `joined_at`, `availability_updated_at`, the `ck_coach_details_assignment_pair` constraint, and `ix_coach_details_trainer`; delete the docstring line saying the single-trainer assignment is out of scope (data-model.md §102, §104)
- [x] T510 [P] Add `availability_updated_at` to `PlayerProfile` in `backend/src/app/models/player_profile.py` (data-model.md §104)
- [x] T511 [P] Add `impersonation_id` to `Session` in `backend/src/app/models/auth.py`, docstringed with the service-maintained invariant of data-model.md §106
- [x] T512 [P] Add `impersonator_user_id` to `AuditEntry` in `backend/src/app/models/audit.py` plus the partial index `ix_audit_entries_impersonator` (data-model.md §107)
- [x] T513 Create `backend/migrations/versions/0011_coach_invitations_availability_impersonation.py` with `down_revision = "0010"`: create the three tables with every constraint and index, then `op.execute` the two `impersonation_sessions` triggers of data-model.md §105
- [x] T514 In the same revision, add the six columns with plain `op.add_column` — and for `audit_entries` **only** plain `op.add_column`, never `op.batch_alter_table`, with the reason as an in-file comment: batch mode recreates the table and silently drops revision 0004's append-only triggers (research.md R2-17)
- [x] T515 Write the reversible `downgrade()` in `backend/migrations/versions/0011_coach_invitations_availability_impersonation.py`: drop the two new triggers, then the three tables, then the six columns
- [x] T516 Create `backend/tests/integration/test_migration_0011.py` asserting, after `upgrade head`: the three tables exist; the six columns exist; **revision 0004's two `audit_entries` triggers still exist**; the two new `impersonation_sessions` triggers exist; and `downgrade` then `upgrade` round-trips cleanly (quickstart.md §1)

**Checkpoint**: `uv run alembic upgrade head` succeeds, T516 passes, `uv run mypy src` clean. Foundation ready — user stories may now proceed.

---

## Phase 3: User Story 1 — A Trainer Invites a Coach and Tracks the Invitation (Priority: P1) 🎯 MVP

**Goal**: a trainer can invite a coach by address with an optional name and message, and can see,
resend, and revoke every invitation they have issued.

**Independent Test**: sign in as a Trainer, invite two addresses, confirm both appear with state and
expiry; resend one and confirm the old link is dead and the list still shows one row for that address;
revoke the other and confirm the link is refused. No coach need accept anything (quickstart.md §2.1 – §2.5).

### Tests for User Story 1

- [x] T517 [P] [US1] Unit-test the presented-state precedence of data-model.md §101.1 in `backend/tests/unit/test_coach_invitation_state.py` — accepted > revoked > superseded > expired > blocked > awaiting, plus `is_usable` ignoring `blocked_at`
- [x] T518 [P] [US1] Integration-test issue and list in `backend/tests/integration/test_coach_invite_issue.py` — 201 with a seven-day `expires_at`, the email file written to the outbox carrying trainer name, message and URL, and **FR-008**: the response is identical in shape and status whether or not the address already holds an account
- [x] T519 [P] [US1] Integration-test resend, revoke, and the duplicate guard in `backend/tests/integration/test_coach_invite_resend_revoke.py` — resend supersedes (old token 404s, list still shows one row), revoke makes the link 404, second issue to a live address returns 409 `coach_invitation_pending` naming the existing invitation, resend of an accepted or revoked row is 422
- [x] T520 [P] [US1] Integration-test isolation and the Active-trainer rule in `backend/tests/integration/test_coach_invite_isolation.py` — another trainer's invitation is a 404 on read, resend, and revoke; a non-Active trainer cannot issue or resend; a coach, player, or parent gets 403
- [x] T521 [P] [US1] Constitution field-clearing tests in `backend/tests/integration/test_coach_invite_null_fields.py` — `invitee_name`/`message` sent as `null` persist as SQL `NULL`, sent as `""` return 422, and omitted keys leave the columns untouched

### Backend implementation for User Story 1

- [x] T522 [US1] Create `backend/src/app/repositories/coach_invitation_repository.py` — `insert`, `get_by_id`, `get_by_token_hash`, `list_for_trainer` (paged, excluding `superseded`), `find_live_for_email`, `mark_revoked`, `mark_superseded`, plus the static `is_usable` predicate of data-model.md §101.2. Queries only, no business rules
- [x] T523 [US1] Create `backend/src/app/schemas/coach_invitation.py` — `CoachInvitationCreate` (`EmailStr`; `invitee_name`/`message` as `str | None` with `min_length=1`), `CoachInvitationOut`, `CoachInvitationPage`, and the presented-state `Literal`, matching contracts/openapi.yaml exactly
- [x] T524 [US1] Create `backend/src/app/services/templates/coach_invitation.py` — `render_coach_invitation_email` returning (subject, body) with the trainer's business name, the optional message, the `{frontend_base_url}/coach-invite/{token}` URL, and the expiry date; no token is ever logged
- [x] T525 [US1] Create `backend/src/app/services/coach_invitation_service.py` with the trainer-side half: `issue` (Active-trainer check, FR-007 duplicate guard raising `CoachInvitationPending`, token generation via `core.security.generate_token`/`hash_token`, email send), `list_for_trainer`, `presented_state`, `resend` (supersede + insert in one transaction), `revoke` — each writing its audit entry per data-model.md §108
- [x] T526 [US1] Add `CoachInvitationServiceDep` to `backend/src/app/core/deps.py` following the existing factory pattern
- [x] T527 [US1] Add the four trainer-side endpoints to `backend/src/app/api/v1/trainer_router.py` — `GET`/`POST /trainer/coach-invitations`, `POST /trainer/coach-invitations/{invitation_id}/resend`, `POST .../revoke` — HTTP concerns only, gated by the existing `TrainerOnlyDep`

### Frontend implementation for User Story 1

- [x] T528 [P] [US1] Add the coach-invitation types of frontend-contracts §37 to `frontend/src/shared/api/types.ts` — `CoachInvitation`, `CoachInvitationPresentedState`, `CoachInvitationBlockReason`, `CoachInvitationPage`, with every nullable field spelled `| null`
- [x] T529 [P] [US1] Create `frontend/src/entities/coach-invitation/api/query-keys.ts` with the `coachInvitationKeys` factory of frontend-contracts §31
- [x] T530 [P] [US1] Create `frontend/src/entities/coach-invitation/model/invitation.ts` — the `coachInvitationCreateSchema` Zod schema of frontend-contracts §32 and the presented-state label map
- [x] T531 [US1] Create the trainer-side hooks: `frontend/src/entities/coach-invitation/api/use-coach-invitations.ts`, `use-issue-coach-invitation.ts`, `use-resend-coach-invitation.ts`, `use-revoke-coach-invitation.ts` — each mutation invalidating `coachInvitationKeys.all` only
- [x] T532 [US1] Create `frontend/src/features/trainer/coach-invitations/ui/invite-coach-form.tsx` — TanStack Form + Zod, routed through `shared/lib/normalize-payload.ts` so `""` becomes `null` before axios (Principle VI), and rendering the 409's existing-invitation body as an offer to resend or revoke
- [x] T533 [US1] Create `frontend/src/features/trainer/coach-invitations/ui/coach-invitation-list.tsx` — one row per invitation showing address, state badge, expiry, and the resend/revoke actions each state permits
- [x] T534 [US1] Create `frontend/src/pages/trainer-coaches/ui/trainer-coaches-page.tsx` composing the form and the list (the roster half arrives in US2)
- [x] T535 [US1] Create the route `frontend/src/routes/_authed/trainer/coaches.tsx` and regenerate `frontend/src/routeTree.gen.ts`
- [x] T536 [US1] Add the Trainer "Coaches" entry to `frontend/src/widgets/app-shell/model/use-nav-items.ts` (`NavItem` union member + `TRAINER_NAV_ITEMS`), with the matching `switch` branch in `frontend/src/widgets/app-shell/ui/primary-nav.tsx` and in `frontend/src/widgets/app-shell/model/use-breadcrumbs.ts` + `ui/app-shell.tsx`
- [x] T537 [P] [US1] Test the invite form in `frontend/tests/features/coach-invitations/invite-coach-form.test.tsx` — msw-backed happy path, `""` normalized to `null` in the request body, 409 rendered as the resend/revoke offer, validation on submit not on keystroke
- [x] T538 [P] [US1] Test the invitation list in `frontend/tests/features/coach-invitations/coach-invitation-list.test.tsx` — one row per state, correct actions enabled per state, no superseded rows
- [x] T539 [P] [US1] Test the page and route in `frontend/tests/pages/trainer-coaches.test.tsx` — a Trainer reaches it; a Coach and a Player/Parent do not
- [x] T540 [US1] Extend `frontend/tests/routes/entry-points.test.tsx` so a Trainer's reachable-path set includes `/trainer/coaches`

**Checkpoint**: US1 fully functional. A trainer issues, tracks, resends, and revokes invitations; a real email file appears in `backend/var/outbox/`. **This is the MVP** — deployable and demonstrable on its own.

---

## Phase 4: User Story 2 — A Coach Accepts an Invitation and Joins Exactly One Trainer (Priority: P1)

**Goal**: the invited person becomes a Coach on the inviting trainer's roster — by registering or by
signing in — sees that trainer's brand, and cannot join a second trainer.

**Independent Test**: follow an invitation as a brand-new person, complete setup, confirm the coach is
on the roster and sees the trainer's branding; then take a second trainer's invitation to the same
coach and confirm it is refused and names no trainer (quickstart.md §2.6 – §2.10).

### Tests for User Story 2

- [x] T541 [P] [US2] Integration-test the register path in `backend/tests/integration/test_coach_invite_register.py` — 201, role `coach`, on the roster with `joined_at`, session cookie set, the request body accepted **without** `email`, `role`, or `trainer_id`, and 409 when an account already exists at the invited address
- [x] T542 [P] [US2] Integration-test the accept path in `backend/tests/integration/test_coach_invite_accept.py` — a coach at the invited address joins; a wrong address is 403 `coach_invitation_address_mismatch` naming the invited address; a non-Coach role is 403 `role_cannot_accept` with no role changed; the FR-016 re-accept is 200 `already_on_this_roster` with no duplicate assignment
- [x] T543 [P] [US2] Integration-test the one-trainer rule and its non-disclosure in `backend/tests/integration/test_coach_one_trainer.py` — 409 `coach_already_assigned`; **assert the full response body and headers contain neither the other trainer's id, name, nor business name (SC-003)**; the invitation is not spent and remains usable; the inviting trainer's list shows it as `blocked`; the block clears on a later successful acceptance
- [x] T544 [P] [US2] Integration-test concurrency and dead links in `backend/tests/integration/test_coach_invite_concurrency.py` — two simultaneous acceptances leave exactly one assignment and one "already used" refusal; spent, revoked, superseded, expired, and non-Active-trainer invitations all return the same 404 body
- [x] T545 [P] [US2] Integration-test the roster in `backend/tests/integration/test_coach_roster.py` — the coach appears with name, address, `joined_at`, status; ending the assignment returns 204, leaves the coach on no roster, keeps their account and profile, and frees them to accept another trainer's invitation; a coach on no roster reaches no trainer's data
- [x] T546 [P] [US2] Integration-test coach branding in `backend/tests/integration/test_coach_branding.py` — a coach on a roster receives that trainer's branding from `GET /auth/session`; a coach on no roster receives the platform default (research.md R2-06)
- [x] T547 [P] [US2] Integration-test the lookup throttle in `backend/tests/integration/test_coach_invite_throttle.py` — repeated unusable tokens from one origin hit 429 with `Retry-After`; a usable token does not count against it (research.md R2-05)

### Backend implementation for User Story 2

- [x] T548 [US2] Extend `backend/src/app/repositories/user_repository.py` with `list_coaches_for_trainer` (paged, `coach_details` joined to `users`, optional name/email filter) and `get_coach_detail` / assignment writes used by the service, per data-model.md §113
- [x] T549 [US2] Add `mark_accepted` to `backend/src/app/repositories/coach_invitation_repository.py` as a **conditional** update guarded on `state = 'awaiting'`, so two concurrent acceptances resolve to one winner (FR-018), plus `set_block` / `clear_block`
- [x] T550 [US2] Create `backend/src/app/schemas/coach.py` — `CoachSummary`, `TrainerCoachSummary`, `TrainerCoachPage`, `CoachInvitationPreview`, `CoachRegistrationRequest`, `CoachJoinResult`, matching contracts/openapi.yaml
- [x] T551 [US2] Add the acceptance half to `backend/src/app/services/coach_invitation_service.py` — `preview` (single refusal path, `account_exists`, trainer identity and branding), `register` (account creation with the address and role taken from the invitation, password policy, `CoachDetail` assignment, session issue), `accept` (FR-016 no-op first, then FR-013 address binding, FR-014 role, FR-015 one-trainer with block annotation), each with its audit entry
- [x] T552 [US2] Create `backend/src/app/services/coach_service.py` — `list_roster` and `end_assignment` (nulling `trainer_user_id`/`joined_at`, writing the `coach_assignment_ended` audit entry), plus `CoachServiceDep` in `backend/src/app/core/deps.py`
- [x] T553 [US2] Create `backend/src/app/api/v1/coach_invitations_router.py` — `GET /coach-invitations/{token}` (`security: []`), `POST .../register` (sets the session cookie exactly as `join_router` does), `POST .../accept`; all three wrapped in the per-origin throttle calls `join_router` already uses
- [x] T554 [US2] Register the new router in `backend/src/app/main.py` and add `GET /trainer/coaches` + `DELETE /trainer/coaches/{coach_user_id}` to `backend/src/app/api/v1/trainer_router.py`
- [x] T555 [US2] Rewrite the Coach branch of `resolve_for_user` in `backend/src/app/services/branding_service.py` to resolve the assigned trainer's branding, falling back to the platform default when unassigned, and **delete the `TODO(US-01.08)` comment** (research.md R2-06)

### Frontend implementation for User Story 2

- [x] T556 [P] [US2] Add `CoachSummary`, `TrainerCoachSummary`, `TrainerCoachPage`, `CoachInvitationPreview`, `CoachJoinResult` to `frontend/src/shared/api/types.ts`, and correct the `CurrentUser.portal_branding` doc comment that says coaches receive the default until US-01.08
- [x] T557 [P] [US2] Create `frontend/src/entities/coach/api/query-keys.ts` with the `coachKeys` factory of frontend-contracts §31
- [x] T558 [US2] Create `frontend/src/entities/coach/api/use-trainer-coaches.ts` and `use-end-coach-assignment.ts` — the mutation invalidating `coachKeys.all` and `availabilityKeys.all`
- [x] T559 [US2] Create `frontend/src/entities/coach-invitation/api/use-coach-invitation-preview.ts`, `use-register-through-coach-invitation.ts`, and `use-accept-coach-invitation.ts` — both mutations invalidating `sessionKey`, since role, trainer, and branding all change
- [x] T560 [US2] Create `frontend/src/features/coach-invite/ui/coach-invite-preview.tsx` — the trainer's identity and brand, the invited address, the message, the expiry, and the register-or-sign-in branch driven by `account_exists`
- [x] T561 [US2] Create `frontend/src/features/coach-invite/ui/coach-registration-form.tsx` — name, password, phone, and the coach profile fields; **no email, role, or trainer input**; the invited address shown read-only
- [x] T562 [US2] Create `frontend/src/features/coach-invite/ui/accept-invitation-panel.tsx` — the signed-in path, rendering each of the four server outcomes (joined, already on this roster, address mismatch, already works with a trainer) with the server's own message and **no hint of another trainer**
- [x] T563 [US2] Create `frontend/src/pages/coach-invite/ui/coach-invite-page.tsx` and the public route `frontend/src/routes/coach-invite.$token.tsx` (typed `token` param, no string-built URL); regenerate `routeTree.gen.ts`
- [x] T564 [US2] Create `frontend/src/features/trainer/coaches/ui/coach-roster-table.tsx` and compose it into `frontend/src/pages/trainer-coaches/ui/trainer-coaches-page.tsx` alongside the invitations half, with the end-assignment confirmation
- [x] T565 [P] [US2] Test the public invite flow in `frontend/tests/features/coach-invite/coach-invite-flow.test.tsx` — preview renders the trainer's brand; registration sends no email/role/trainer; each refusal renders its message; **assert no rendered text contains another trainer's name**
- [x] T566 [P] [US2] Test the roster in `frontend/tests/features/coach-invitations/coach-roster-table.test.tsx` and the route in `frontend/tests/routes/coach-invite.test.tsx` — an unusable token renders the single refusal, not a stack trace

**Checkpoint**: US1 + US2 complete — the whole of US-01.08. A stranger becomes a coach on a roster, sees the trainer's brand, cannot join a second trainer, and can be released by the trainer.

---

## Phase 5: User Story 3 — A Coach Sets Their My Times (Priority: P2)

**Goal**: a coach states, revises, and clears a weekly pattern of ranges, saved whole and validated
before anything is written.

**Independent Test**: as a coach, state times on three days including two ranges on one day, save, sign
out and in, confirm the week reads back exactly; submit overlapping ranges and confirm refusal with the
day named and the stored week unchanged (quickstart.md §3.1 – §3.3).

### Tests for User Story 3

- [x] T567 [P] [US3] Unit-test the whole-week validator in `backend/tests/unit/test_availability_validation.py` — overlap detection, touching ranges accepted, `start >= end` refused, past-midnight refused, off-grid refused, seven-ranges-in-a-day refused, and the day named in every failure (FR-027, FR-028)
- [x] T568 [P] [US3] Integration-test the coach's own week in `backend/tests/integration/test_availability_own.py` — never-stated returns `{slots: [], updated_at: null}`; a save returns the week ordered by `(day_of_week, start_minute)`; two non-overlapping ranges on one day both persist; the week survives a sign-out/sign-in round trip (SC-007)
- [x] T569 [P] [US3] Integration-test refusals leave state untouched in `backend/tests/integration/test_availability_refusals.py` — after each invalid submission the stored week is byte-identical to before (FR-027, SC-008)
- [x] T570 [P] [US3] Integration-test clearing in `backend/tests/integration/test_availability_clear.py` — `DELETE` returns 204 and leaves `slots: []` with a **non-null** `updated_at`, distinct from never-stated (FR-030, FR-032, FR-035)
- [x] T571 [P] [US3] Integration-test role scoping in `backend/tests/integration/test_availability_scope.py` — `/me/availability` is Coach-only; a coach cannot reach anyone else's week by any route (FR-033, FR-036)

### Backend implementation for User Story 3

- [x] T572 [US3] Create `backend/src/app/repositories/availability_repository.py` — `list_for_coach`, `list_for_profile`, `list_for_profiles` (one `IN` query for a page), `delete_for_owner`, `insert_many`, and the owner-timestamp writes; queries only
- [x] T573 [US3] Create `backend/src/app/schemas/availability.py` — `AvailabilitySlotModel` (field bounds and the 15-minute step as Pydantic constraints), `AvailabilityWeekOut`, `AvailabilityWeekUpdate`, matching contracts/openapi.yaml
- [x] T574 [US3] Create `backend/src/app/services/availability_service.py` — the set-level validator of data-model.md §111.2 (validate everything first, raising `ValidationFailure` keyed by day), then `replace_week` / `clear_week` / `get_week` for either owner kind, each in one transaction and stamping `availability_updated_at`
- [x] T575 [US3] Add `AvailabilityServiceDep` to `backend/src/app/core/deps.py`
- [x] T576 [US3] Add `GET`/`PUT`/`DELETE /me/availability` to `backend/src/app/api/v1/me_router.py`, gated Coach-only via the existing `require_roles` factory

### Frontend implementation for User Story 3

- [x] T577 [P] [US3] Add `AvailabilitySlot` and `AvailabilityWeek` to `frontend/src/shared/api/types.ts`
- [x] T578 [P] [US3] Create `frontend/src/entities/availability/model/week.ts` — the constants, the `availabilitySlotSchema`, and the `availabilityWeekSchema` with the set-level `superRefine` of frontend-contracts §32, attaching each issue to the offending day's path
- [x] T579 [P] [US3] Create `frontend/src/entities/availability/model/format-summary.ts` — **the only formatter in the app**: slots → `"Mon 5–8pm, Wed 6–9pm"`, slots → full-week rows, and the three "no times set" rules of frontend-contracts §34
- [x] T580 [P] [US3] Create `frontend/src/entities/availability/api/query-keys.ts` with the `AvailabilitySubject` discriminated union and the `availabilityKeys` factory of frontend-contracts §31
- [x] T581 [US3] Create `frontend/src/entities/availability/api/use-availability.ts`, `use-save-availability.ts`, `use-clear-availability.ts` — one hook each, taking an `AvailabilitySubject`, invalidating only that subject's key
- [x] T582 [US3] Create `frontend/src/features/availability/ui/day-ranges-field.tsx` and `availability-week-editor.tsx` — **one form for the whole week** (frontend-contracts §33), add/remove ranges per day, a quarter-hour picker, and the server's day-keyed 422 mapped onto the right day
- [x] T583 [US3] Create `frontend/src/pages/my-times/ui/my-times-page.tsx` and the route `frontend/src/routes/_authed/my-times.tsx`; regenerate `routeTree.gen.ts`
- [x] T584 [US3] Add the Coach "My Times" nav entry to `frontend/src/widgets/app-shell/model/use-nav-items.ts` — replacing `coach`'s empty list and correcting the comment that says the role has no page — with the matching branches in `primary-nav.tsx`, `use-breadcrumbs.ts`, and `app-shell.tsx`
- [x] T585 [P] [US3] Unit-test the model and formatter in `frontend/tests/entities/availability/week.test.ts` and `format-summary.test.ts` — including the never-stated vs cleared distinction and that no day is ever rendered "Unavailable"
- [x] T586 [P] [US3] Test the editor and page in `frontend/tests/features/availability/availability-week-editor.test.tsx` and `frontend/tests/pages/my-times.test.tsx`; extend `frontend/tests/routes/entry-points.test.tsx` for the coach's now-non-empty nav

**Checkpoint**: a coach states and revises a week; every invalid week is refused with the day named and changes nothing.

---

## Phase 6: User Story 4 — A Parent Sets Availability Separately for Themselves and Each Child (Priority: P2)

**Goal**: one account, several player profiles, strictly separated weeks — reached through the profile
switcher the family already uses.

**Independent Test**: as a parent with two children, state a different week per profile and confirm each
reads back against the right profile; as the child, confirm only their own week is reachable
(quickstart.md §3.4 – §3.6).

### Tests for User Story 4

- [x] T587 [P] [US4] Integration-test per-profile separation in `backend/tests/integration/test_availability_family.py` — saving one child's week leaves the sibling's and the parent's own untouched; each reads back against the right profile
- [x] T588 [P] [US4] Integration-test sibling and account isolation in `backend/tests/integration/test_availability_isolation.py` — a signed-in child reaches their own profile (200) and a sibling's or the parent's own (**404, not 403**); an unrelated account gets 404; the parent may revise what a child stated (FR-033, SC-009)
- [x] T589 [P] [US4] Integration-test the FR-039 lifecycle in `backend/tests/integration/test_availability_lifecycle.py` — removing a profile deletes its slots and no route returns them; erasing an account deletes its slots; a coach's slots survive their assignment ending

### Backend implementation for User Story 4

- [x] T590 [US4] Add `GET`/`PUT`/`DELETE /me/players/{profile_id}/availability` to `backend/src/app/api/v1/family_router.py`, resolving ownership through the existing `FamilyService` path so parent, child, and sibling behaviour are inherited rather than re-implemented (research.md R2-11)
- [x] T591 [US4] Extend `backend/src/app/services/family_service.py` so profile removal deletes that profile's availability slots in the same transaction (data-model.md §114)
- [x] T592 [US4] Extend `backend/src/app/services/erasure_service.py` to delete the erased account's availability slots alongside the personal data it already removes (data-model.md §114)

### Frontend implementation for User Story 4

- [x] T593 [US4] Create `frontend/src/pages/availability/ui/availability-page.tsx` — the same `availability-week-editor` widget, with the profile switcher choosing the subject, and the selected profile's name unmistakable on screen
- [x] T594 [US4] Create the route `frontend/src/routes/_authed/availability.tsx`; regenerate `routeTree.gen.ts`
- [x] T595 [US4] Add the Player/Parent "Availability" nav entry to `frontend/src/widgets/app-shell/model/use-nav-items.ts` — shown to a signed-in **child as well as** a parent, unlike Approvals/Requests (frontend-contracts §36) — with the branches in `primary-nav.tsx`, `use-breadcrumbs.ts`, and `app-shell.tsx`
- [x] T596 [P] [US4] Test the page in `frontend/tests/pages/availability.test.tsx` — switching profiles switches the week; the on-screen subject is unambiguous; a child sees only their own
- [x] T597 [P] [US4] Extend `frontend/tests/routes/entry-points.test.tsx` so both parent and child variants of `player_parent` reach `/availability`
- [x] T598 [P] [US4] Test that saving one profile's week does not refetch another's in `frontend/tests/entities/availability/query-keys.test.ts` (invalidation is per subject, frontend-contracts §31)
- [x] T599 [US4] Add the shared "no times set" empty state to `frontend/src/features/availability/ui/availability-week-view.tsx` so both the editor and the read-only view render absence identically
- [x] T600 [P] [US4] Integration-test the constitution's field-clearing pair for the availability endpoints in `backend/tests/integration/test_availability_null_fields.py` — an empty `slots` array clears the week and stamps `updated_at`; a malformed body leaves it untouched

**Checkpoint**: US3 + US4 complete — every person and profile can state times, with strict family isolation.

---

## Phase 7: User Story 5 — A Trainer Reads the Stated Times of Their Coaches and Players (Priority: P2)

**Goal**: the trainer sees a summary, the full week, and the revision date for the people connected to
them — and for nobody else.

**Independent Test**: with a coach and three players (one with no times stated), sign in as their trainer
and confirm each record shows the right summary or "no times set", and that a player belonging only to
another trainer appears nowhere (quickstart.md §4).

### Tests for User Story 5

- [x] T601 [P] [US5] Integration-test the trainer's reads in `backend/tests/integration/test_availability_trainer_view.py` — coach and player weeks with `updated_at`; a person with nothing stated reads as empty-with-null rather than absent; the roster rows carry slots
- [x] T602 [P] [US5] Integration-test the boundaries in `backend/tests/integration/test_availability_trainer_isolation.py` — another trainer's coach is 404; a profile with no Active association is 404; ending an association makes the read 404 **immediately**; a coach reading anyone else's times is refused (FR-036, SC-009)
- [x] T603 [P] [US5] Integration-test read-only-ness and no-N+1 in `backend/tests/integration/test_availability_trainer_writes.py` — no write method exists on any `/trainer/**/availability` path (405), and a 25-row roster page issues **one** availability query, asserted by counting statements on the session (FR-037, data-model.md §113)
- [x] T604 [P] [US5] Integration-test FR-038 in `backend/tests/integration/test_availability_never_gates.py` — with a coach and player who have stated nothing, every action available to them succeeds; nothing anywhere is refused on availability grounds (SC-011)

### Backend implementation for User Story 5

- [x] T605 [US5] Add `GET /trainer/coaches/{coach_user_id}/availability` and `GET /trainer/players/{profile_id}/availability` to `backend/src/app/api/v1/trainer_router.py`, each scoped to the caller's own roster / Active association
- [x] T606 [US5] Add the roster-scoped read methods to `backend/src/app/services/availability_service.py` and `coach_service.py`, authorizing through the same query that selects the data (research.md R2-11)
- [x] T607 [US5] Extend `backend/src/app/services/trainer_service.py` and `backend/src/app/schemas/trainer_player.py` so `TrainerPlayerSummary` carries `availability` and `availability_updated_at`, populated by the single `list_for_profiles` `IN` query

### Frontend implementation for User Story 5

- [x] T608 [P] [US5] Add `availability` and `availability_updated_at` to `TrainerPlayerSummary` in `frontend/src/shared/api/types.ts`
- [x] T609 [US5] Create `frontend/src/features/availability/ui/availability-summary.tsx` — the one-line summary for list rows, reading `format-summary.ts`; never renders "Unavailable"
- [x] T610 [US5] Add the summary column to `frontend/src/widgets/trainer-roster-table/ui/trainer-roster-table.tsx` and to the coach roster table, with the revision date beside it
- [x] T611 [US5] Create `frontend/src/pages/coach-detail/ui/coach-detail-page.tsx` plus the route `frontend/src/routes/_authed/trainer/coaches.$coachUserId.tsx` showing the coach's full week read-only; regenerate `routeTree.gen.ts`
- [x] T612 [P] [US5] Test the summary and detail views in `frontend/tests/features/availability/availability-summary.test.tsx` and `frontend/tests/pages/coach-detail.test.tsx` — "no times set" for an unstated week, a stale revision date shown, and no control anywhere that would edit another person's times

**Checkpoint**: US-01.09 and US-01.10's availability half is complete end to end — data, ownership, and the trainer's read.

---

## Phase 8: User Story 6 — A Super Admin Views the Platform as Another Person (Priority: P3)

**Goal**: impersonation that is exact, visible, time-boxed, and attributable — with no second session
and no per-endpoint work.

**Independent Test**: impersonate a trainer; confirm the view, data, and permissions are that trainer's,
the banner is on every view, Super-Admin-only routes are unreachable, Exit returns without
re-authentication, and impersonating a Super Admin is refused (quickstart.md §5.1 – §5.7).

### Tests for User Story 6

- [x] T613 [P] [US6] Unit-test the rules in `backend/tests/unit/test_impersonation_rules.py` — who may impersonate whom; end-reason selection including the FR-042-vs-FR-050 `target_status_at_start` logic (research.md R2-19)
- [x] T614 [P] [US6] Integration-test starting in `backend/tests/integration/test_impersonation_start.py` — 201; `/auth/session` then describes the target with an `impersonation` block; the same cookie; a second start supersedes the first (FR-048)
- [x] T615 [P] [US6] Integration-test exactness in `backend/tests/integration/test_impersonation_effective_user.py` — every `/admin/**` route 403s, the target's own routes 200, and the target's data is what is returned, for each of the three impersonable roles (FR-043, SC-016)
- [x] T616 [P] [US6] Integration-test every refusal in `backend/tests/integration/test_impersonation_guards.py` — Super Admin target, self, erased target all 422; an Inactive target succeeds and is labelled; nested impersonation, deactivate, and erase are each refused **explicitly asserted, not assumed** (FR-042, FR-047, R2-15)
- [x] T617 [P] [US6] Integration-test exit and timeout in `backend/tests/integration/test_impersonation_exit_timeout.py` — exit succeeds **while the effective user is a Trainer** (the asymmetric route, R2-15); a session past its deadline resolves to the admin with `impersonation_ended.end_reason = timed_out`; no impersonation exceeds the ceiling (SC-014)
- [x] T618 [P] [US6] Integration-test non-interference in `backend/tests/integration/test_impersonation_isolation.py` — the impersonated person's sessions are untouched, they are not signed out or notified, and their expiry advances only from their own activity (FR-049)
- [x] T619 [P] [US6] Integration-test dual attribution in `backend/tests/integration/test_impersonation_audit.py` — a change made while impersonating writes one audit entry naming the target as `actor_user_id` **and** the admin as `impersonator_user_id`; an ordinary change leaves the column `NULL` (FR-052, SC-015)
- [x] T620 [P] [US6] Integration-test the lifecycle hooks in `backend/tests/integration/test_impersonation_lifecycle.py` — sign-out (`signed_out`), target deactivation when it started Active (`target_deactivated`), an Inactive-at-start target staying Inactive (**does not end**), erasure (`target_erased`), and the admin's own deactivation (`admin_deactivated`) (FR-050)

### Backend implementation for User Story 6

- [x] T621 [US6] Create `backend/src/app/core/principal.py` — frozen `ImpersonationContext` and `Principal(effective_user, real_user, impersonation)` dataclasses (research.md R2-14)
- [x] T622 [US6] Create `backend/src/app/repositories/impersonation_repository.py` — `insert`, `close` (the one permitted update), `get_open_for_admin`, `get_by_id`, `list_filtered` (paged, by admin / target / date range), `most_recent_ended_for_admin`. **No update or delete method beyond `close`**, mirroring `AuditRepository`'s append-only construction
- [x] T623 [US6] Create `backend/src/app/schemas/impersonation.py` — `ImpersonationCreate`, `ImpersonationOut` (with computed `duration_seconds`), `ImpersonationParticipant`, `ImpersonationPage`, matching contracts/openapi.yaml
- [x] T624 [US6] Create `backend/src/app/services/impersonation_service.py` — `start` (the FR-042 guards, `target_status_at_start`, superseding an open row, setting `sessions.impersonation_id`, both audit entries), `end` (close + clear pointer), `resolve_for_session` (the deadline and FR-050 checks returning the end reason), `history`
- [x] T625 [US6] Refactor `backend/src/app/core/deps.py`: add `get_principal` resolving the effective user and stamping `db_session.info["impersonator_user_id"]`; re-express `get_current_user` as a one-line wrapper over it so **no existing endpoint signature changes**; add `get_impersonation_context`; add `ImpersonationServiceDep` (research.md R2-14, R2-16)
- [x] T626 [US6] Add the real-identity dependency for the exit route to `backend/src/app/core/deps.py` — an Active Super Admin `real_user` holding an open impersonation — and document why it must not use `require_roles(SUPER_ADMIN)` (research.md R2-15)
- [x] T627 [US6] Make `AuditRepository.add` in `backend/src/app/repositories/audit_repository.py` read `AsyncSession.info["impersonator_user_id"]` into the new column — the single choke point, docstringed with R2-16's justification
- [x] T628 [US6] Create `backend/src/app/api/v1/impersonations_router.py` with `POST /admin/impersonations` and `DELETE /admin/impersonations/current`, and register it in `backend/src/app/main.py`
- [x] T629 [US6] Extend `backend/src/app/schemas/auth.py` (`CurrentUser`) and `backend/src/app/api/v1/auth_router.py` so `GET /auth/session` carries `impersonation` and the derived `impersonation_ended` (120-second look-back, excluding `exited`) (research.md R2-20)
- [x] T630 [US6] Extend `backend/src/app/services/auth_service.py` so `sign_out` closes an open impersonation as `signed_out` before revoking the session
- [x] T631 [US6] Extend `backend/src/app/services/user_admin_service.py` so deactivation closes any open impersonation on either side, in the same transaction as the status change and the existing session revocation
- [x] T632 [US6] Extend `backend/src/app/services/erasure_service.py` so erasure closes any open impersonation of the erased account as `target_erased` while **keeping** every history row

### Frontend implementation for User Story 6

- [x] T633 [P] [US6] Add `Impersonation`, `ImpersonationParticipant`, `ImpersonationEndReason`, `ImpersonationPage` to `frontend/src/shared/api/types.ts`, plus `impersonation` and `impersonation_ended` on `CurrentUser`
- [x] T634 [P] [US6] Create `frontend/src/entities/impersonation/api/query-keys.ts`
- [x] T635 [US6] Create `frontend/src/entities/impersonation/api/use-start-impersonation.ts` and `use-end-impersonation.ts` — each invalidating `sessionKey` and then `await queryClient.clear()`, the app's only two sanctioned uses (frontend-contracts §35), then navigating to `/`
- [x] T636 [US6] Create `frontend/src/app/store/impersonation-notice-slice.ts` — the Zustand UI slice holding which impersonation ids have had their end-reason toast shown
- [x] T637 [US6] Create `frontend/src/widgets/impersonation-banner/ui/impersonation-banner.tsx` — persistent, token-based destructive styling, naming the impersonated person and the acting admin, a display-only countdown to `expires_at`, and an Exit control; renders `null` when `session.impersonation` is `null`
- [x] T638 [US6] Render `<ImpersonationBanner />` above `<AppShell />` in `frontend/src/routes/_authed.tsx`, plus the end-reason toast via `sonner`, deduplicated through the slice from T636
- [x] T639 [US6] Create `frontend/src/features/admin/impersonation/ui/impersonate-action.tsx` and `impersonation-confirm-dialog.tsx` — the directory-row action and the confirmation naming the person and role (FR-040), wired into `frontend/src/widgets/user-directory-table/`
- [x] T640 [P] [US6] Test the banner in `frontend/tests/widgets/impersonation-banner.test.tsx` — present whenever `impersonation` is set, absent otherwise, never derived from a role mismatch, countdown decorative only
- [x] T641 [P] [US6] Test the start/exit mutations in `frontend/tests/features/impersonation/impersonation-mutations.test.tsx` — both call `queryClient.clear()`; a Super Admin's cached directory page cannot survive into the impersonated portal
- [x] T642 [P] [US6] Test the confirm dialog and row action in `frontend/tests/features/impersonation/impersonate-action.test.tsx` — no Impersonate control on a Super Admin row or the caller's own row
- [x] T643 [P] [US6] Test that existing route guards need no impersonation-specific code in `frontend/tests/routes/impersonated-guards.test.tsx` — a session describing a Trainer is redirected away from `/admin/users` by the existing guard (FR-043)

**Checkpoint**: impersonation is live, exact, visible, bounded, and attributable.

---

## Phase 9: User Story 7 — A Super Admin Reviews the Impersonation History (Priority: P3)

**Goal**: an unforgeable, filterable record of every impersonation the platform has ever permitted.

**Independent Test**: perform three impersonations ending three different ways; confirm each appears once
with the right participants, times, duration and end reason; confirm each filter returns the right
subset; confirm no route alters or removes an entry (quickstart.md §5.8 – §5.9).

### Tests for User Story 7

- [x] T644 [P] [US7] Integration-test the history in `backend/tests/integration/test_impersonation_history.py` — every impersonation appears once with both participants, times, duration and end reason; an in-progress one shows `ended_at: null` and `duration_seconds: null`; each of the four filters returns exactly its subset (FR-053, FR-054)
- [x] T645 [P] [US7] Integration-test access in `backend/tests/integration/test_impersonation_history_access.py` — Trainer, Coach, and Player/Parent each get 403, refused on the request (FR-056)
- [x] T646 [P] [US7] Integration-test tamper-proofing in `backend/tests/integration/test_impersonation_append_only.py` — direct `DELETE` and `UPDATE` against `impersonation_sessions` both abort; closing an **open** row succeeds; re-closing a closed row aborts; `audit_entries`' original two triggers still abort (FR-055)
- [x] T647 [P] [US7] Integration-test erasure survival in `backend/tests/integration/test_impersonation_history_erasure.py` — after the impersonated account is erased, the row still stands and names the account by identifier with the anonymized display name (FR-055, SC-017)

### Backend implementation for User Story 7

- [x] T648 [US7] Add `GET /admin/impersonations` with the four filters to `backend/src/app/api/v1/impersonations_router.py`, Super-Admin-gated and paged
- [x] T649 [US7] Add `history` filtering and participant resolution to `backend/src/app/services/impersonation_service.py`, resolving display names through `UserRepository` so an erased account renders its anonymized name

### Frontend implementation for User Story 7

- [x] T650 [P] [US7] Create `frontend/src/entities/impersonation/model/history-search.ts` — the URL-owned filter schema with `.catch()` fallbacks of frontend-contracts §32
- [x] T651 [US7] Create `frontend/src/entities/impersonation/api/use-impersonations.ts` reading the search params
- [x] T652 [US7] Create `frontend/src/features/admin/impersonation/ui/impersonation-history-table.tsx` and `frontend/src/pages/admin-impersonations/ui/admin-impersonations-page.tsx` — both participants, start, end, duration, end reason, in-progress rows marked
- [x] T653 [US7] Create the route `frontend/src/routes/_authed/admin/impersonations.tsx` with `validateSearch` from T650, add the Super Admin "Impersonation history" nav entry in `frontend/src/widgets/app-shell/model/use-nav-items.ts` and the matching `switch` branches; regenerate `routeTree.gen.ts`
- [x] T654 [P] [US7] Test the history page in `frontend/tests/pages/admin-impersonations.test.tsx` and `frontend/tests/features/impersonation/impersonation-history-table.test.tsx` — filters live in the URL and survive a reload; in-progress rows render without a duration; extend `frontend/tests/routes/entry-points.test.tsx`

**Checkpoint**: all seven stories complete. Epic-01 is closed.

---

## Phase 10: Polish & Cross-Cutting Concerns

- [x] T655 Extend `backend/tests/contract/test_openapi_contract.py` to validate the live OpenAPI document against the **union** of `specs/001-user-roles-admin/contracts/openapi.yaml` and `specs/002-coach-availability-impersonation/contracts/openapi.yaml` — every path, method, status code, and required response field at v1.3.0
- [x] T656 [P] Add `backend/tests/integration/test_no_internal_leakage_002.py` extending feature 001's equivalent — no new endpoint returns a driver message, ORM traceback, token, or token hash in any error path
- [x] T657 [P] Add `backend/tests/integration/test_permission_matrix_002.py` — every new endpoint × every role, asserted against contracts/openapi.yaml's declared status codes, refused on the request rather than by a hidden control
- [x] T658 [P] Run the feature-specific greps of quickstart.md §6 and fix any hit: no `any`, axios only in `shared/api`, no raw SQL outside revision 0011's triggers, no `batch_alter_table` on `audit_entries`, no trainer identity in an already-assigned refusal, no availability-based gate, no server-side summary formatting
- [x] T659 [P] Verify every new nullable text field declares `str | None` with `min_length=1` and that every new form submit path routes through `frontend/src/shared/lib/normalize-payload.ts` (Principle VI); fix any exception
- [x] T660 Walk quickstart.md §2 – §5 end to end against a fresh database and correct any step whose expected output no longer matches
- [x] T661 [P] Measure the two performance claims: a 25-row coach roster and a 25-row player roster each issue one availability query, and impersonation adds at most two indexed reads per request (plan.md Performance Goals)
- [x] T662 [P] Update `backend/README.md` and `frontend/README.md` with the two new settings, the new routes, and the coach-invitation email flow
- [x] T663 [P] Update the role-capability tables in `backend/README.md` and `specs/002-coach-availability-impersonation/quickstart.md` so the Coach's My Times entry and the Trainer's Coaches entry appear wherever each role's reachable pages are enumerated
- [x] T664 Delete every stale comment this feature invalidated: `branding_service.py`'s `TODO(US-01.08)` (if T555 missed it), `use-nav-items.ts`'s "coach has no page", `types.ts`'s "Coaches receive the default until US-01.08", `role_details.py`'s "single-trainer assignment is out of scope", and `enums.py`'s `COACH_SINGLE_USE` promise
- [x] T665 [P] Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, and `uv run pytest -q` in `backend/`; fix everything
- [x] T666 [P] Run `npm run lint`, `npm run typecheck`, and `npm run test` in `frontend/`; fix everything, including the `eslint-plugin-boundaries` FSD import-direction rule
- [x] T667 Check off every completed task in this file, so `tasks.md` remains an accurate record of what exists (constitution: Development Workflow §5)
- [x] T668 Record the two Open Items of plan.md as resolved or still open — coach joins as Active with no pending step, and impersonation permits action rather than being read-only — in a short note appended to `plan.md`

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no dependencies; T500 → T503 → T504 in order (config before errors before handlers); T501 and T502 are `[P]`
- **Phase 2 (Foundational)**: depends on Phase 1. **Blocks every user story.** T505 first (the enums the models import), then T506 – T512 in parallel, then T513 – T515 sequentially (one file), then T516
- **Phase 3 (US1, P1)**: depends on Phase 2 only
- **Phase 4 (US2, P1)**: depends on Phase 2, and on **T522, T523, T525** from US1 — it extends the same repository, schema module, and service. This is the one deliberate cross-story dependency: US-01.08's two halves share one invitation aggregate, and splitting it into two services to avoid the dependency would be worse
- **Phase 5 (US3, P2)**: depends on Phase 2 only — fully independent of US1/US2
- **Phase 6 (US4, P2)**: depends on Phase 2, and on **T572 – T575, T578 – T582** from US3 (the shared repository, service, week model, and editor widget — research.md R2-07's whole point)
- **Phase 7 (US5, P2)**: depends on Phase 2, on US3's service (T574) for the read, and on US2's roster (T548, T552) for the coach half. The player half depends only on US3
- **Phase 8 (US6, P3)**: depends on Phase 2 only. Sequenced **last among implementation phases** because T625 refactors the dependency every other endpoint resolves its caller through: landing it after Phases 3 – 7 means their tests, written without impersonation in mind, become the regression suite proving FR-043
- **Phase 9 (US7, P3)**: depends on Phase 8 (it reads what Phase 8 writes)
- **Phase 10 (Polish)**: depends on every story phase that is being delivered

### Within each user story

- Tests are written first and **must fail** before the implementation they cover
- Models → repositories → services → routers → frontend entities → features → pages → routes → nav
- A story's checkpoint must pass before the next story starts, when working sequentially

### Same-file serialization (no two tasks may hold the same file)

| File | Held by, in order |
|---|---|
| `backend/src/app/core/deps.py` | T526 → T552 → T575 → T625 → T626 |
| `backend/src/app/main.py` | T504 → T554 → T628 |
| `backend/src/app/models/enums.py` | T505 only |
| `backend/src/app/api/v1/trainer_router.py` | T527 → T554 → T605 |
| `backend/src/app/services/coach_invitation_service.py` | T525 → T551 |
| `backend/src/app/repositories/coach_invitation_repository.py` | T522 → T549 |
| `backend/src/app/services/availability_service.py` | T574 → T606 |
| `backend/src/app/api/v1/impersonations_router.py` | T628 → T648 |
| `backend/src/app/services/impersonation_service.py` | T624 → T649 |
| `frontend/src/shared/api/types.ts` | T528 → T556 → T577 → T608 → T633 |
| `frontend/src/widgets/app-shell/model/use-nav-items.ts` (+ `primary-nav.tsx`, `use-breadcrumbs.ts`, `app-shell.tsx`) | T536 → T584 → T595 → T653 |
| `frontend/src/routeTree.gen.ts` | regenerated by T535, T563, T583, T594, T611, T653 — never hand-edited |
| `frontend/tests/routes/entry-points.test.tsx` | T540 → T586 → T597 → T654 |
| `frontend/src/pages/trainer-coaches/ui/trainer-coaches-page.tsx` | T534 → T564 |

### Parallel opportunities

- Phase 2: T506, T507, T508, T510, T511, T512 — six model files, all independent after T505
- Every story's test tasks are `[P]` with each other: T517 – T521, T541 – T547, T567 – T571, T587 – T589, T601 – T604, T613 – T620, T644 – T647
- US3 and US1 can be built by two developers simultaneously after Phase 2 — they share no file
- US6 can be built alongside US1/US3 by a third developer **only** if T625's `deps.py` refactor is scheduled last; otherwise it conflicts with T526, T552, and T575
- Phase 10: T656 – T659, T661 – T663, T665, T666 are all `[P]`

---

## Parallel Example: Phase 2 models

```bash
# After T505 (enums) lands, six model files with no shared file:
Task: "Create CoachInvitation model in backend/src/app/models/coach_invitation.py"
Task: "Create AvailabilitySlot model in backend/src/app/models/availability.py"
Task: "Create ImpersonationSession model in backend/src/app/models/impersonation.py"
Task: "Add availability_updated_at to backend/src/app/models/player_profile.py"
Task: "Add impersonation_id to backend/src/app/models/auth.py"
Task: "Add impersonator_user_id to backend/src/app/models/audit.py"
```

## Parallel Example: User Story 1 tests

```bash
# All five fail before T522 – T527 exist:
Task: "Unit-test presented-state precedence in backend/tests/unit/test_coach_invitation_state.py"
Task: "Integration-test issue and list in backend/tests/integration/test_coach_invite_issue.py"
Task: "Integration-test resend/revoke/duplicate in backend/tests/integration/test_coach_invite_resend_revoke.py"
Task: "Integration-test isolation in backend/tests/integration/test_coach_invite_isolation.py"
Task: "Field-clearing tests in backend/tests/integration/test_coach_invite_null_fields.py"
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Phase 1 Setup (T500 – T504)
2. Phase 2 Foundational (T505 – T516) — **blocking**
3. Phase 3 User Story 1 (T517 – T540)
4. **STOP and VALIDATE**: quickstart.md §2.1 – §2.5
5. Demo: a trainer invites coaches and tracks every invitation. Nothing else in the feature is required for that to be true.

### Incremental delivery

| Increment | Phases | Demonstrates |
|---|---|---|
| 1 | 1 – 3 | A trainer issues and tracks coach invitations (MVP) |
| 2 | 4 | US-01.08 complete: coaches join, one trainer each, branded portal |
| 3 | 5 – 6 | Everyone can state a week; families stay isolated |
| 4 | 7 | US-01.09 / US-01.10's availability half complete: trainers read the times |
| 5 | 8 – 9 | US-01.07 complete: impersonation and its history — **Epic-01 closed** |
| 6 | 10 | Gates, greps, docs, and stale-comment cleanup |

Each increment leaves the product working and adds value without breaking the previous one.

### Parallel team strategy

With three developers, after Phase 2 lands:

- **Developer A**: Phase 3 → Phase 4 (the coach-invitation vertical; owns `coach_invitation_*`)
- **Developer B**: Phase 5 → Phase 6 → Phase 7 (the availability vertical; owns `availability_*`)
- **Developer C**: Phase 8 → Phase 9, holding T625/T626 until A and B have merged (the impersonation vertical; owns `impersonation_*`)

The three verticals share only `core/deps.py`, `main.py`, `shared/api/types.ts`, and the nav module —
all four serialized in the table above.

---

## Traceability

| Requirements | Tasks |
|---|---|
| FR-001 – FR-010 (issue, track, resend, revoke) | T517 – T527, T532 – T536 |
| FR-011 – FR-019 (accept, one trainer, block) | T541 – T544, T549 – T553, T559 – T563 |
| FR-020 – FR-023 (roster, end assignment, audit) | T545, T548, T552, T554, T564 |
| FR-024, FR-026 – FR-032 (state a week) | T567 – T576, T578 – T583 |
| FR-025, FR-033 (per profile, who may state) | T587 – T590, T593 – T595 |
| FR-034 – FR-037 (the trainer's read, read-only) | T601 – T603, T605 – T611 |
| FR-038 (availability never gates) | T604, T658 |
| FR-039 (lifecycle) | T589, T591, T592 |
| FR-040 – FR-044 (start, exactness, banner) | T613 – T616, T621 – T625, T637 – T639 |
| FR-045 – FR-050 (exit, ceiling, ending) | T617, T618, T620, T626, T629 – T632, T638 |
| FR-051, FR-052 (record, dual attribution) | T619, T622, T624, T627 |
| FR-053 – FR-056 (history) | T644 – T649, T650 – T654 |
| SC-003 (non-disclosure) | T543, T562, T565, T658 |
| SC-009 (isolation) | T588, T602, T657 |
| SC-014 – SC-016 (bounds, tamper-proofing, exactness) | T615 – T617, T646 |
| Constitution field-clearing gate | T521, T600, T659 |
| Contract fidelity | T655 |

---

## Notes

- `[P]` means a different file and no dependency on an incomplete task; the serialization table is authoritative where the two seem to conflict
- Every test task must be seen to **fail** before its implementation task begins
- Commit after each task or each logical group; check the box in this file as it lands (T667 is the backstop, not the plan)
- The one cross-story dependency (US2 on US1's invitation aggregate) is deliberate and explained above; every other story is independently testable at its checkpoint
- Two decisions in `plan.md`'s Open Items are cheap to reverse **before** Phase 4 and Phase 8 respectively, and expensive after; confirm them before starting those phases
