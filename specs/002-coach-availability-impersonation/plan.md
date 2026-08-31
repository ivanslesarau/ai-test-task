# Implementation Plan: Coach Invitations, Availability ("My Times") & Super Admin Impersonation

**Branch**: `002-coach-availability-impersonation` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-coach-availability-impersonation/spec.md`

**Companion artifacts**: [research.md](./research.md) (22 decisions, `R2-nn`) ·
[data-model.md](./data-model.md) (§101 – §114) · [contracts/openapi.yaml](./contracts/openapi.yaml)
(v1.3.0) · [contracts/frontend-contracts.md](./contracts/frontend-contracts.md) (§30 – §38) ·
[quickstart.md](./quickstart.md)

---

## Summary

This feature closes Epic-01 by building the three stories feature 001 deliberately deferred: a trainer
invites a coach onto their roster (US-01.08), every coach and player profile states a weekly
availability that their trainers can read (US-01.09, US-01.10), and a Super Admin views the platform as
another person under an auditable, time-boxed impersonation (US-01.07). 56 functional requirements, 7
prioritized user stories, 18 success criteria.

**The technical approach in four sentences.** Coach invitations get their own hashed-token,
single-use, seven-day table rather than a second `share_links` kind, because the two secrets have
opposite security postures and opposite disclosure rules (R2-01); the one-trainer-per-coach rule
becomes a nullable `trainer_user_id` on `coach_details`, making the cardinality true by construction
rather than by a checked count (R2-04). Availability is one table serving both owner kinds, times as
integer minutes on a quarter-hour grid, replaced whole-week in one transaction, with the revision date
on the owner's own row so a cleared week is still distinguishable from one never stated (R2-07 – R2-10).
Impersonation creates **no second session and no second auth path**: the admin's existing session row
gains a nullable pointer, and one refactored dependency substitutes the effective user, which makes
"exactly what that person sees and can do" true for the whole existing API and every endpoint later
epics add (R2-14). Dual attribution of changes made under impersonation is achieved with one new
`audit_entries` column fed from the request's own database session, so no service signature changes
(R2-16) — the single deliberate deviation in this plan, recorded in Complexity Tracking.

**Delivery shape**: one additive Alembic revision (0011), three new tables, seven new columns, three
new backend service/repository pairs, two extended routers plus two new ones, and one frontend slice
per concept. No new dependency in either `pyproject.toml` or `package.json`.

**Two things this plan does not build**, both excluded by the spec with reasons: the roster-wide
availability filter and the coach-to-event conflict warning with a trainer override. Both need an event
or a roster-wide query that does not exist in the platform; this feature produces exactly the data they
will read.

---

## Technical Context

**Language/Version**: Python 3.13 (backend); TypeScript 5.7 in strict mode on React 19 (frontend).
Both fixed by the constitution's ratified stack.

**Primary Dependencies**: FastAPI ≥ 0.115 on uvicorn; SQLAlchemy 2.0 async with aiosqlite; Alembic;
Pydantic V2 with pydantic-settings; pwdlib[argon2]; aiosmtplib. Frontend: TanStack Router / Query /
Form, Zod, Zustand, axios, Tailwind 4 with shadcn/ui, sonner. **No dependency is added by this
feature** — every capability it needs is already installed (R2-21).

**Storage**: SQLite via `sqlite+aiosqlite`, one Alembic revision (0011). Three new tables
(`coach_invitations`, `availability_slots`, `impersonation_sessions`), seven new columns across four
existing tables, two new triggers. No data migration: every added column is nullable and correct as
`NULL` for every existing row (data-model.md §110).

**Testing**: pytest ≥ 8.3 with pytest-asyncio in auto mode, httpx, over `tests/unit`,
`tests/integration`, `tests/contract`. Frontend: vitest 3 with jsdom, Testing Library, msw.

**Target Platform**: Linux/Windows server for the API; evergreen browsers for the SPA.

**Project Type**: Web application — `backend/` (layered FastAPI service) plus `frontend/`
(Feature-Sliced React SPA), as feature 001 established.

**Performance Goals**: inherited from Epic-01 §11 — dashboard under 2 s, a paged list of 10,000 rows
under 3 s, a save under 1 s. This feature's own budget items: the coach roster and player roster must
carry availability **without an N+1** (one `IN` query per page, data-model.md §113); the impersonation
resolution must add at most two indexed primary-key reads per request (R2-14).

**Constraints**:
- Availability is guidance only. Nothing in the platform may block, refuse, or delay an action on the
  grounds of stated times (FR-038) — a constraint on what may *not* be built.
- No scheduler exists, so both time limits (the seven-day invitation, the one-hour impersonation) are
  enforced on read, never by a background job (R2-03, R2-19).
- `audit_entries` must never be altered with Alembic batch mode: it would silently drop the
  append-only triggers feature 001 installed (R2-17).
- The already-assigned refusal must not disclose the other trainer, through any field, message, or
  view (FR-015, SC-003).

**Scale/Scope**: 56 FRs; 15 new or extended endpoints; at most 42 availability slots per person by
construction; 6 new frontend routes; ~14 new backend modules and ~24 new frontend modules.

---

## Constitution Check

*GATE: evaluated before Phase 0 and re-evaluated after Phase 1 design. Constitution v1.1.1.*

| Principle | Pre-Phase-0 | Post-Phase-1 verdict |
|---|---|---|
| **I. Spec-Driven Development** | spec.md written and validated (16/16 checklist) before any design | **PASS.** This plan and its four companions exist before any code; `tasks.md` follows before implementation. No functional code has been written |
| **II. End-to-End Type Safety** | Every new payload is a Pydantic V2 model; every new frontend type mirrors it | **PASS.** contracts/openapi.yaml is the single source both sides mirror; frontend-contracts §37 lists the added types, all with `\| null` rather than `?`. Zero `any`; the `AvailabilitySubject` discriminated union (§31) is what keeps the one availability hook typed without one |
| **III. Layered Backend Architecture** | Three new service/repository pairs planned; routers hold HTTP only | **PASS with one recorded deviation.** Router → service → repository throughout, all deps via `Depends`. The deviation is the `AsyncSession.info` carrier for the impersonator id (R2-16), recorded in Complexity Tracking with its rejected alternative |
| **IV. Feature-Sliced Frontend** | One slice per concept, imports downward only | **PASS.** `entities/{coach,coach-invitation,availability,impersonation}` own their server state and models; `features/*` compose; `widgets/impersonation-banner` is rendered by the layout route. No cross-slice imports; the shared summary formatter lives in the entity that owns the concept, not duplicated into two features |
| **V. Async-First Persistence & Contained Failures** | All new I/O `async`; SQLAlchemy 2.0 constructs only | **PASS.** One exception, pre-existing in kind: revision 0011's `CREATE TRIGGER` statements are literal SQL because triggers are not expressible in Core — exactly as revision 0004 already does. Every new domain error maps to one status code and the single `Error` envelope |
| **VI. Null-Not-Empty Data Contract** | Every new optional field is nullable | **PASS.** `invitee_name`, `message`, and the optional coach profile fields are `str \| None` with `min_length=1`; forms route through the existing `shared/lib/normalize-payload.ts`; the two constitution-mandated field-clearing tests are named in quickstart §6 |
| **Configuration** | Two new settings | **PASS.** `COACH_INVITATION_TTL_DAYS` and `IMPERSONATION_MAX_MINUTES` are required, no defaults, added to `.env.example`. Availability's invariants are module constants, not configuration, because they must match a CHECK constraint (R2-21) |
| **Design tokens** | No new colors | **PASS.** The impersonation banner uses the destructive/warning token role; no ad-hoc hex value anywhere (frontend-contracts §35) |
| **Migrations** | One versioned revision | **PASS.** Revision 0011, reviewed alongside the code that needs it, with the R2-17 caution as an in-file comment |

**Gate result: PASS.** One deviation, justified and recorded below.

---

## Project Structure

### Documentation (this feature)

```text
specs/002-coach-availability-impersonation/
├── spec.md                        # Written and validated 2026-08-28
├── plan.md                        # This file
├── research.md                    # Phase 0 — 22 decisions (R2-01 … R2-22)
├── data-model.md                  # Phase 1 — §101 … §114
├── quickstart.md                  # Phase 1 — validation walk-through and quality gates
├── contracts/
│   ├── openapi.yaml               # Phase 1 — contract v1.3.0, additive
│   └── frontend-contracts.md      # Phase 1 — routes, query keys, state ownership (§30 … §38)
├── checklists/
│   └── requirements.md            # Spec quality checklist, 16/16
└── tasks.md                       # Phase 2 — NOT created by /speckit-plan
```

### Source Code (repository root)

**Backend — new files**

```text
backend/
├── migrations/versions/
│   └── 0011_coach_invitations_availability_impersonation.py
├── src/app/
│   ├── core/
│   │   ├── availability_rules.py          # 15-minute grid, 6/day, 7 days, bounds (R2-21)
│   │   └── principal.py                   # frozen Principal + ImpersonationContext dataclasses
│   ├── models/
│   │   ├── coach_invitation.py            # data-model.md §101
│   │   ├── availability.py                # §103
│   │   └── impersonation.py               # §105
│   ├── repositories/
│   │   ├── coach_invitation_repository.py
│   │   ├── availability_repository.py
│   │   └── impersonation_repository.py    # insert / close / select only — no update, no delete
│   ├── schemas/
│   │   ├── coach_invitation.py
│   │   ├── availability.py
│   │   ├── coach.py                       # CoachSummary, TrainerCoachSummary/Page
│   │   └── impersonation.py
│   ├── services/
│   │   ├── coach_invitation_service.py
│   │   ├── coach_service.py               # roster read, end assignment
│   │   ├── availability_service.py        # one service, both owner kinds (R2-07)
│   │   ├── impersonation_service.py
│   │   └── templates/coach_invitation.py  # the invitation email
│   └── api/v1/
│       ├── coach_invitations_router.py    # public: preview / register / accept
│       └── impersonations_router.py       # /admin/impersonations
└── tests/
    ├── unit/
    │   ├── test_coach_invitation_state.py       # presented-state precedence (§101.1)
    │   ├── test_availability_validation.py      # overlap, grid, ceiling, touching ranges
    │   └── test_impersonation_rules.py          # who may impersonate whom; end-reason selection
    ├── integration/
    │   ├── test_coach_invite_issue.py           # FR-001 – FR-008, FR-010
    │   ├── test_coach_invite_resend_revoke.py   # FR-005, FR-006
    │   ├── test_coach_invite_register.py        # FR-011, FR-013, FR-017
    │   ├── test_coach_invite_accept.py          # FR-012 – FR-019
    │   ├── test_coach_one_trainer.py            # FR-015 + SC-003 non-disclosure
    │   ├── test_coach_roster.py                 # FR-020, FR-021, FR-022
    │   ├── test_coach_branding.py               # R2-06
    │   ├── test_availability_own.py             # FR-024, FR-026 – FR-032
    │   ├── test_availability_family.py          # FR-025, FR-033, sibling isolation
    │   ├── test_availability_trainer_view.py    # FR-034 – FR-037, no N+1
    │   ├── test_availability_lifecycle.py       # FR-039: removal, erasure, association end
    │   ├── test_impersonation_start.py          # FR-040 – FR-043, FR-048
    │   ├── test_impersonation_guards.py         # FR-042, FR-047 — each refusal explicitly
    │   ├── test_impersonation_exit_timeout.py   # FR-045, FR-046
    │   ├── test_impersonation_audit.py          # FR-052 dual attribution
    │   ├── test_impersonation_history.py        # FR-053 – FR-056
    │   └── test_impersonation_append_only.py    # the two new triggers
    └── contract/test_openapi_contract.py        # extended to the union of both contract files
```

**Backend — files changed**

| File | Change | Reference |
|---|---|---|
| `models/enums.py` | Add `CoachInvitationState` (+ transitions), `CoachInvitationBlockReason`, `ImpersonationEndReason`; **remove** `ShareLinkKind.COACH_SINGLE_USE` and correct its docstring | §109 |
| `models/role_details.py` | `CoachDetail`: `trainer_user_id`, `joined_at`, `availability_updated_at` + pair constraint | §102 |
| `models/player_profile.py` | `PlayerProfile.availability_updated_at` | §104 |
| `models/auth.py` | `Session.impersonation_id` | §106 |
| `models/audit.py` | `AuditEntry.impersonator_user_id` | §107 |
| `repositories/audit_repository.py` | `add` reads `AsyncSession.info["impersonator_user_id"]` — the one choke point | R2-16 |
| `repositories/user_repository.py` | Coach roster query joining `coach_details.trainer_user_id` | §113 |
| `core/deps.py` | `get_principal` (new, cached) → `get_current_user` / `get_impersonation_context`; three new service deps; the real-identity dependency for the exit route | R2-14, R2-15 |
| `core/config.py` | `coach_invitation_ttl_days`, `impersonation_max_minutes` | R2-21 |
| `core/errors.py` | `CoachInvitationPending`, `CoachAlreadyAssigned`, `CoachAddressMismatch`, `RoleCannotAccept`, `ImpersonationNotPermitted`, `InvitationNotResendable` | contracts |
| `main.py` | Exception handlers for the six new errors; register the two new routers | — |
| `api/v1/trainer_router.py` | Coach invitations (list/issue/resend/revoke), coach roster, end assignment, the two trainer-side availability reads; `/trainer/players` rows gain availability | contracts |
| `api/v1/me_router.py` | `/me/availability` GET/PUT/DELETE (coach) | contracts |
| `api/v1/family_router.py` | `/me/players/{profile_id}/availability` GET/PUT/DELETE | contracts |
| `api/v1/auth_router.py` | `/auth/session` carries `impersonation` and `impersonation_ended` | R2-20 |
| `services/branding_service.py` | Coach branch resolves the assigned trainer's branding; delete the `TODO(US-01.08)` | R2-06 |
| `services/family_service.py` | Profile removal deletes that profile's slots | §114 |
| `services/erasure_service.py` | Delete slots; end any open impersonation of the erased account | §114 |
| `services/user_admin_service.py` | Deactivation ends open impersonations on either side | §114 |
| `services/auth_service.py` | Sign-out closes an open impersonation first | §114 |
| `schemas/auth.py` | `CurrentUser` gains the two blocks | contracts |
| `schemas/trainer_player.py` | `TrainerPlayerSummary` gains availability fields | contracts |
| `.env.example` | The two new keys | R2-21 |

**Frontend — new files**

```text
frontend/src/
├── entities/
│   ├── coach/api/{query-keys,use-trainer-coaches,use-end-coach-assignment}.ts
│   ├── coach-invitation/
│   │   ├── api/{query-keys,use-coach-invitations,use-issue-coach-invitation,
│   │   │        use-resend-coach-invitation,use-revoke-coach-invitation,
│   │   │        use-coach-invitation-preview,use-accept-coach-invitation,
│   │   │        use-register-through-coach-invitation}.ts
│   │   └── model/invitation.ts                 # Zod schema, presented-state labels
│   ├── availability/
│   │   ├── api/{query-keys,use-availability,use-save-availability,use-clear-availability}.ts
│   │   └── model/{week,format-summary}.ts      # the ONLY formatter (R2-12)
│   └── impersonation/
│       ├── api/{query-keys,use-start-impersonation,use-end-impersonation,use-impersonations}.ts
│       └── model/history-search.ts             # URL-owned filters
├── features/
│   ├── trainer/coach-invitations/ui/{invite-coach-form,coach-invitation-list}.tsx
│   ├── trainer/coaches/ui/coach-roster-table.tsx
│   ├── coach-invite/ui/{coach-invite-preview,coach-registration-form,accept-invitation-panel}.tsx
│   ├── availability/ui/{availability-week-editor,availability-week-view,availability-summary,
│   │                    day-ranges-field}.tsx
│   └── admin/impersonation/ui/{impersonate-action,impersonation-confirm-dialog,
│                               impersonation-history-table}.tsx
├── widgets/impersonation-banner/ui/impersonation-banner.tsx
├── pages/
│   ├── trainer-coaches/ui/trainer-coaches-page.tsx
│   ├── coach-detail/ui/coach-detail-page.tsx
│   ├── my-times/ui/my-times-page.tsx
│   ├── availability/ui/availability-page.tsx
│   ├── coach-invite/ui/coach-invite-page.tsx
│   └── admin-impersonations/ui/admin-impersonations-page.tsx
└── routes/
    ├── coach-invite.$token.tsx
    └── _authed/
        ├── my-times.tsx
        ├── availability.tsx
        ├── trainer/coaches.tsx
        ├── trainer/coaches.$coachUserId.tsx
        └── admin/impersonations.tsx
```

**Frontend — files changed**

| File | Change |
|---|---|
| `shared/api/types.ts` | The types in frontend-contracts §37; two `CurrentUser` fields; two `TrainerPlayerSummary` fields; correct the `portal_branding` doc comment |
| `routes/_authed.tsx` | Render `<ImpersonationBanner />` above `AppShell`, and the end-reason toast |
| `widgets/app-shell/model/use-nav-items.ts` | Four new `NavItem` members; `coach` no longer empty; correct the stale comment |
| `widgets/app-shell/ui/primary-nav.tsx`, `app-shell.tsx`, `model/use-breadcrumbs.ts` | One `switch` branch per new route |
| `app/store/*` | One small UI slice: impersonation-notice ids already shown |
| `widgets/trainer-roster-table/*` | Availability summary column |
| `routeTree.gen.ts` | Regenerated |

**Frontend — tests** mirror the structure: `tests/features/{coach-invitations,availability,impersonation}/`,
`tests/widgets/impersonation-banner.test.tsx`, `tests/pages/{my-times,availability,trainer-coaches,admin-impersonations}.test.tsx`,
`tests/routes/entry-points.test.tsx` (extended — the coach's list is no longer empty), and
`tests/entities/availability/{week,format-summary}.test.ts`.

**Structure Decision**: the existing two-project layout is kept exactly as feature 001 established it —
`backend/src/app/{api,core,db,models,repositories,schemas,services}` with `tests/{unit,integration,contract}`,
and `frontend/src/{app,entities,features,pages,routes,shared,widgets}` with `tests/` mirroring. Every
new file above lands in the layer its content belongs to; no new top-level directory is introduced.

---

## Implementation Sequence

Six phases. Each ends at a demonstrable state, and the order follows the spec's own priorities (P1
coach invitations, P2 availability, P3 impersonation) with one exception noted below. Within a phase,
migration → model → repository → service → router → tests → frontend, because each layer is the
previous one's only dependency.

**Phase 16 — Schema and shared foundations** *(prerequisite for everything)*

Revision 0011 in full (data-model.md §110, and R2-17's caution about `audit_entries`); the three
models; the three enums plus the `ShareLinkKind` removal; `core/availability_rules.py`; the two new
settings and `.env.example`; the six domain errors and their handlers. Ends with `alembic upgrade head`
plus quickstart §1's trigger-survival check passing.

*Numbering continues from feature 001's phases 1 – 15, so a task id is unique across the repository.*

**Phase 17 — Coach invitations, trainer side** *(US1, P1)*

`coach_invitation_repository`, `coach_invitation_service` (issue, list, resend, revoke, presented
state), the `/trainer/coach-invitations` endpoints, the invitation email template, the FR-023 audit
entries. Frontend: the `coach-invitation` entity, the invite form, the invitation list, the
`/trainer/coaches` route rendering the invitations half. Demonstrable: a trainer issues, tracks,
resends, and revokes invitations; a real email file appears.

**Phase 18 — Coach acceptance and the roster** *(US2, P1)*

`coach_service` (roster, end assignment); the acceptance half of `coach_invitation_service` (the
address binding, the role check, the one-trainer rule and its block annotation, the FR-016 no-op, the
concurrent-acceptance guard); `coach_invitations_router` (preview/register/accept) with the reused
per-IP throttle; the `CoachDetail` assignment writes; the `BrandingService` Coach branch (R2-06).
Frontend: the public `/coach-invite/$token` route, the registration form, the roster table, the
Coaches nav entry. Demonstrable: a stranger becomes a coach on a roster, sees the trainer's brand, and
cannot join a second trainer.

**Phase 19 — Availability, the owner's side** *(US3 + US4, P2)*

`availability_repository`, `availability_service` (the whole-week validator and the atomic replace),
`/me/availability` and `/me/players/{profile_id}/availability`, the FR-039 lifecycle hooks in
`family_service` and `erasure_service`. Frontend: the `availability` entity (week model, Zod schema,
the one formatter), the week editor widget, `/my-times`, `/availability`, and the two nav entries.
Demonstrable: a coach and a parent state weeks; every invalid week is refused with the day named and
changes nothing.

**Phase 20 — Availability, the trainer's side** *(US5, P2)*

The two trainer-side read endpoints; availability embedded in both roster payloads with the single
`IN` query (§113); the read-only week view and the summary column. Demonstrable: a trainer reads their
coaches' and players' times, sees "no times set" where nothing is stated, and cannot reach anyone
else's.

**Phase 21 — Impersonation** *(US6 + US7, P3)*

`impersonation_repository` (insert/close/select only), `impersonation_service`, the `core/principal.py`
dataclasses and the `core/deps.py` refactor (`get_principal` → `get_current_user` +
`get_impersonation_context`), the real-identity gate for the exit route, `impersonations_router`, the
`AuditRepository` dual attribution, the `/auth/session` extension, and the four lifecycle hooks
(sign-out, deactivate, erase, supersede). Frontend: the banner in `routes/_authed.tsx`, the directory
row action and its dialog, the history page, the end-reason toast, and `queryClient.clear()` on both
boundaries. Demonstrable: quickstart §5 end to end.

**Why impersonation is last despite touching the most shared code**: it is the only phase that
modifies the authentication path every other phase depends on. Landing it after the other four means
its `get_principal` refactor is exercised against a codebase whose new endpoints already exist and are
already tested — so an endpoint that behaves differently under impersonation fails a test that was
written before impersonation existed.

**Same-file serialization**: `core/deps.py`, `main.py`, `models/enums.py`,
`widgets/app-shell/model/use-nav-items.ts`, and `shared/api/types.ts` are touched by four phases each.
`tasks.md` must serialize those edits — no two tasks may hold the same file — exactly as feature 001's
plan did for its own shared files.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Request-scoped state on `AsyncSession.info`** carries the impersonator's id from `get_principal` to `AuditRepository.add` (R2-16), rather than passing it through `Depends` into every service. Principle III requires dependencies to be supplied through `Depends`; it forbids *global or module-level* mutable state, which this is not — `info` is per-request state on an object already injected via `Depends`. | FR-052 requires that **every** change made during an impersonation names both parties. Audit writes originate in ~12 services, each taking `actor_user_id` as a method argument from its router. | Threading a second identity parameter through `AuditRepository.add` and every audit-writing service method means ~15 signature changes for a case none of those services can reason about, and it is silently wrong the first time a future author forgets the argument — the failure mode is a missing audit fact, which is exactly what must not be possible. The chosen carrier is read in exactly one function, so there is one place to verify and one place to test. |
| **Literal SQL** in revision 0011 for two `CREATE TRIGGER` statements. | The append-only guarantee for `impersonation_sessions` (FR-055) must survive a script that bypasses the repository, and triggers are not expressible as SQLAlchemy ORM or Core constructs. | There is no Core construct for a trigger. This is the same, already-accepted exception revision 0004 took for `audit_entries`; no new class of deviation is introduced, and it is confined to a migration. |

**Considered and found *not* to be violations** (recorded so a reviewer need not re-derive them):

- **Removing an enum value** (`ShareLinkKind.COACH_SINGLE_USE`) is not a schema change requiring a
  migration: no row has ever carried it, because `insert_standing_link` is the only writer of
  `share_links.kind` and writes `PLAYER_STANDING` unconditionally (R2-01, §109.4).
- **One table for two owner kinds** with two nullable FKs is not a polymorphic-association smell: the
  CHECK constraint makes exactly one owner true by construction, and both FKs are real, so referential
  integrity holds in both directions (R2-07).
- **Formatting the availability summary on the client** is not business logic leaking into the UI: the
  server sends structured minutes, and day names and clock format are presentation (R2-12).
- **`queryClient.clear()`** on the two impersonation boundaries is not a cache-management shortcut: every
  cached response belongs to the previous identity, and leaving it in place would be a client-side
  data-isolation failure (frontend-contracts §35).

---

## Open items to raise before implementation

Neither blocks `/speckit-tasks`; both are decisions the client may wish to overturn, and each is
cheap to change *before* Phase 18 and 21 respectively.

1. **A coach joins as Active, with no trainer confirmation step** (spec Assumptions, FR-017). US-01.08
   offers "Pending or Active". If the client wants a pending state, it is one column on
   `coach_details` and one endpoint, added in Phase 18 — but retrofitting it after the roster UI exists
   costs more.
2. **Impersonation permits action, forbidding only account takeover** (spec Assumptions, FR-047). If the
   client wants a strictly read-only impersonation, that is a different Phase 21: a write-blocking
   dependency on every mutating route, and the FR-052 dual-attribution machinery becomes unnecessary.
   The spec explicitly rejected read-only, so this is a confirmation, not a question.

### Resolution (2026-08-31, tasks.md T668)

No contradicting instruction arrived during implementation, so both items shipped exactly as planned
rather than as open — recorded here as the record of what was actually built, not as a still-pending
decision:

1. **Resolved as planned.** A coach joins Active on acceptance, with no pending state
   (`CoachInvitationService.accept`/`register`, T551; `coach_details.trainer_user_id` set the moment
   the invitation is accepted). No pending-confirmation column or endpoint exists. If the client later
   wants one, Phase 18's own note above still describes exactly what it would take.
2. **Resolved as planned.** Impersonation permits action: the effective-user substitution
   (`core/deps.py::get_principal`, T625) lets an impersonating admin do anything the target account
   could do, and FR-047's four account-takeover paths — credential change, deactivate, erase, nested
   impersonation — are the only actions refused, each structurally (the effective user fails the
   relevant role gate) rather than by a special-cased check. Every action taken while impersonating is
   dual-attributed in `audit_entries` (`impersonator_user_id`, T627), verified by
   `test_impersonation_audit.py`. No read-only mode was built.
