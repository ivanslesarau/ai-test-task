# Phase 0 Research: Coach Invitations, Availability & Impersonation

**Feature**: `002-coach-availability-impersonation` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)

**Purpose**: Settle every design question `plan.md`, `data-model.md`, and `contracts/` depend on, so
those documents contain no unknowns. The specification carries no `[NEEDS CLARIFICATION]` markers, so
none of the decisions below resolve one; they resolve *how* to build what the spec already fixed, on
top of the code feature 001 actually left behind.

**Numbering**: decisions are `R2-nn`, deliberately distinct from feature 001's `R-nn`. Existing source
comments cite `research.md R-21` and similar, meaning 001's document; a new comment citing `R2-06`
cannot be confused with them.

**Note on sources**: no library version choices are made here — the stack is fixed by the
constitution and every dependency this feature needs is already installed. The decisions rest on the
existing code (cited by file and line-level fact) and on architectural reasoning. Nothing here
required external documentation, so no Context7 lookups were performed.

**Verified state of the codebase as of 2026-08-28** (the factual base for everything below):

| Fact | Where |
|---|---|
| `ShareLinkKind.COACH_SINGLE_USE` exists as a forward declaration; no row of that kind is ever written | `backend/src/app/models/enums.py` |
| `ShareLink.code` is stored **in clear**, deliberately, because a trainer must read it back | `backend/src/app/models/share_link.py`, `core/security.py:generate_share_link_code` |
| `CredentialSetupInvitation` stores only a SHA-256 `token_hash`, with `consumed_at` **and** `superseded_at` | `backend/src/app/models/auth.py` |
| `CoachDetail` has **no** trainer-assignment column | `backend/src/app/models/role_details.py` |
| A `CoachDetail` row is created for every coach account at creation time | `backend/src/app/repositories/user_repository.py:161` |
| Nothing named availability, my-times, or best-times exists anywhere in the backend or frontend | repository-wide search |
| Nothing named impersonation exists anywhere | repository-wide search |
| `audit_entries` is append-only and protected by two SQLite triggers created in revision 0004 | `migrations/versions/0004_create_audit_and_erasure.py` |
| `BrandingService.resolve_for_user` returns the platform default for a Coach, with a `TODO(US-01.08)` | `backend/src/app/services/branding_service.py:62` |
| `CurrentUser.portal_branding` documents "Coaches receive the default until US-01.08" | `frontend/src/shared/api/types.ts` |
| `navItemsForRole('coach')` returns `[]`, documented as correct "for this feature" | `frontend/src/widgets/app-shell/model/use-nav-items.ts` |
| Migration head is `0010`; the next revision is `0011` | `backend/migrations/versions/` |

---

## Part A — Coach invitations (US-01.08, FR-001 – FR-023)

### R2-01: A dedicated `coach_invitations` table, not a second `share_links` kind

**Decision**: Coach invitations get their own table. `ShareLinkKind.COACH_SINGLE_USE` is **not** used;
its docstring is corrected to record that US-01.08 chose a dedicated table, and the value is removed
in the same revision-free edit because no row has ever carried it and nothing but the enum references
it.

**Rationale**: feature 001 left the enum value as a courtesy — "declared so US-01.08 is additive
rather than a restructuring". Taking the courtesy would cost more than it saves, on four counts:

1. **The secret has the opposite security posture.** `share_links.code` is stored in clear on purpose:
   FR-069 of feature 001 requires the trainer to read the code back and print it on a flyer, and its
   confidentiality is explicitly not a security property. A coach invitation is a single-use secret
   mailed to one named person; the project already has a table for exactly that shape
   (`credential_setup_invitations`) and it stores only a hash. Putting both spellings in one `code`
   column — clear for player rows, hashed for coach rows — is the one option that is worse than
   either.
2. **Five extra columns would be permanently NULL on every player row.** `invitee_name`, `message`,
   `accepted_by_user_id`, `accepted_at`, `blocked_at`, `blocked_reason` mean nothing for a standing
   player link.
3. **The lifecycles differ.** A standing link is one live row per trainer, never expiring, unlimited
   uses, and `ShareLinkRepository.get_current_for_trainer` assumes exactly that. A coach invitation is
   many rows per trainer, one per invited address, each with its own expiry and its own five-state
   lifecycle including supersession.
4. **The refusal messages differ, and 001's are deliberately uniform.**
   `ShareLinkService.resolve_usable_link` funnels six distinct failures into one indistinguishable
   `InvitationLinkInvalid`, so a stranger cannot learn which condition failed. FR-013 requires the
   *opposite* for coach invitations: name the address the invitation was issued for. Branching that
   service on kind would put a disclosure rule and a non-disclosure rule in one function.

**Alternatives considered**:

| Alternative | Rejected because |
|---|---|
| Reuse `share_links` with `kind = coach_single_use` | The four reasons above; the "additive" saving is one `CREATE TABLE`, paid for with a mixed-secret column and a branching refusal path. |
| Reuse `share_links` for the code, plus a `coach_invitation_details` side table | Two rows per invitation, two writes per state change, and the mixed-secret problem survives. |
| Reuse `credential_setup_invitations` | It is keyed to an existing `users` row; a coach invitation exists precisely when no account need exist yet. |

**Consequence for feature 001's documents**: `specs/001-user-roles-admin/spec.md`'s Out of Scope note
("the invitation link record carries a kind so this can be added without restructuring") stays true as
written — nothing was restructured — but the kind is not what carried it. No 001 artifact is edited.

### R2-02: Hashed single-use token, seven-day expiry, resend by supersession

**Decision**: `coach_invitations.token_hash` holds a SHA-256 of a `secrets.token_urlsafe(32)` token
generated by the existing `core.security.generate_token` / `hash_token` pair. The raw token exists
only inside the emailed URL. Expiry is `issued_at + settings.coach_invitation_ttl_days` (7). Resend
marks the current row `superseded` and inserts a fresh row for the same address.

**Rationale**: this is `CredentialSetupInvitation`'s exact shape, including its `superseded_at`
column, which already models "re-issuing invalidates the previous outstanding link" — FR-005 word for
word. Reusing the two security helpers means no new crypto surface, and a leaked database yields no
usable invitation. Supersession rather than mutation keeps the audit trail honest: the row that was
mailed on Tuesday is still the row that was mailed on Tuesday.

**Alternatives considered**: mutating the existing row's token and expiry in place (loses the record
of what was actually sent, and makes FR-023's audit entries unverifiable); allowing two live
invitations per address (FR-005 forbids it, and it makes "which link admitted this coach" ambiguous).

### R2-03: Four stored states, expiry derived, `blocked` as an annotation

**Decision**: `coach_invitations.state` stores only the four **event-driven** states — `awaiting`,
`accepted`, `revoked`, `superseded` — and *expired* is derived at read time from `expires_at` when the
state is `awaiting`. `blocked` is not a state at all: it is a pair of nullable columns
(`blocked_at`, `blocked_reason`) on a row that remains `awaiting`. Presentation precedence, applied in
one function: `accepted` > `revoked` > `superseded` > `expired` > `blocked` > `awaiting`.

**Rationale**: three separate forces converge on this shape.

- Storing `expired` would need a writer — either a background job the project does not have, or a
  lazy write on read that turns every GET into a database write and takes SQLite's single write lock.
  Feature 001 already made this call twice: `ShareLinkRepository.is_usable` derives expiry, and the
  approvals feature derives nothing else but keeps its transitions explicit. Deriving is the cheaper
  and non-racy half.
- FR-015 says an acceptance refused because the coach already works elsewhere **must not spend the
  invitation**, while FR-019 says the trainer must see it as blocked. Those two are only compatible if
  "blocked" does not consume or terminate the row. As an annotation, the invitation stays live: the
  coach who leaves their trainer on Thursday can accept Friday's still-valid link, and the block
  clears on success.
- FR-005 lets a trainer resend an invitation "awaiting a response or expired". If `blocked` were a
  terminal state, a blocked invitation would be resendable by neither rule and the trainer would be
  stuck.

**Alternatives considered**: a six-value enum with a transition table like `ApprovalRequestStatus`
(needs an expiry writer, and makes `blocked → awaiting` a transition that means "nothing actually
happened"); deriving `blocked` from the audit trail instead of columns (a list view would have to join
`audit_entries` per row and interpret free text).

### R2-04: The assignment is two columns on `coach_details`, not an association table

**Decision**: add `trainer_user_id` (nullable FK to `users.id`) and `joined_at` (nullable) to
`coach_details`. Ending an assignment sets both to NULL. The history of past assignments lives in
`audit_entries` (FR-023) and in the accepted `coach_invitations` rows.

**Rationale**: FR-015 is "at most one trainer per coach at any time", and a nullable column on a table
that already has exactly one row per coach makes that true *by construction* — there is no shape in
which two assignments can exist, so no unique index, no service-level count check, and no race. A
`coach_trainer_assignments` table with a partial unique index would express the same rule less
directly and would need a status column, a transition rule, and a "which row is current" query, all to
model a relation whose cardinality is one.

The entity note in the spec — "ending it leaves the coach unattached rather than erasing the record of
having been attached" — is satisfied without a history table: FR-023 requires the audit entry, and the
accepted invitation row keeps `accepted_by_user_id` and `accepted_at` forever.

**Alternatives considered**: a dedicated assignment table with history (buys a queryable employment
timeline no requirement asks for, at the cost of two sources of truth for "who is my trainer");
reusing `trainer_player_associations` (its subject is a player profile, and a coach has none).

### R2-05: Acceptance reuses the join flow's three-endpoint shape and its throttle

**Decision**: coach acceptance is `GET /coach-invitations/{token}` (public preview),
`POST /coach-invitations/{token}/register` (no account yet — creates the Coach account, assigns, signs
in), and `POST /coach-invitations/{token}/accept` (signed-in coach). The per-origin guessing throttle
reuses `LinkLookupAttemptRepository` and `ShareLinkService.check_lookup_throttle`'s configured
threshold, exactly as `join_router` does.

**Rationale**: the player join flow solved the same three problems — a public preview that must not
leak, a register-and-sign-in path that sets the session cookie, and an accept path for someone already
signed in — and its router is 101 lines of already-reviewed code to pattern-match. Reusing the
throttle repository is reuse of a table and a predicate, not of a semantic: both are "someone is
trying codes at this IP", which is the one dimension either link exposes.

The preview returns `account_exists` for the invited address. This is not the enumeration leak FR-008
forbids: FR-008 protects the *trainer* from learning whether an address is registered, and the
preview is gated on possession of a 256-bit token that was mailed to that address.

**Alternatives considered**: a single `POST /coach-invitations/{token}/accept` that branches on whether
a session cookie is present (conflates "create an account" and "attach an account", and makes the
201/200 distinction impossible); putting coach acceptance on `/join/{code}` (see R2-01's fourth
point — the two refusal policies contradict).

### R2-06: Coach branding closes an existing documented TODO

**Decision**: `BrandingService.resolve_for_user`'s Coach branch resolves the assigned trainer's
branding, exactly as the Trainer branch does, falling back to the platform default when the coach is
on no roster. The `TODO(US-01.08)` comment and the `CurrentUser.portal_branding` doc comment on the
frontend are both updated.

**Rationale**: Story 2 requires the accepting coach to land in a portal carrying the trainer's brand,
and feature 001 left this branch stubbed with the reason "which trainer a coach works for is US-01.08".
R2-04 supplies that fact, so the stub becomes a two-line branch. Leaving the TODO in place after its
blocker is gone is precisely the failure the constitution's own v1.1.1 amendment was written to correct.

---

## Part B — Availability (US-01.09, US-01.10, FR-024 – FR-039)

### R2-07: One `availability_slots` table for both subject kinds, with an exactly-one-of check

**Decision**: a single table whose rows carry `coach_user_id` (nullable FK `users.id`) **and**
`player_profile_id` (nullable FK `player_profiles.id`), with a CHECK constraint that exactly one is
non-NULL. One shared repository, one shared service, one shared frontend editor widget.

**Rationale**: FR-024 and FR-025 describe the same object stated by two different kinds of owner, and
FR-026 to FR-032 are identical for both — same ranges, same validation, same atomic replace, same
"no times set". Two tables would duplicate every rule and every test, and the trainer-side read
(FR-034) would need two code paths to produce one screen. Two real foreign keys with a CHECK beat a
polymorphic `(subject_kind, subject_id)` pair because referential integrity survives: a slot cannot
point at a profile that does not exist, and `ON DELETE CASCADE` does the right thing for a hard
delete.

**Alternatives considered**: `availability_slots` per subject type, i.e. two tables (duplicates the
whole rule set); polymorphic subject columns (no FK, so nothing stops an orphan, and every query needs
a discriminator filter anyway); a JSON column holding the whole week (unqueryable by the roster-wide
filter Epic-02/03 will add — the one consumer this feature is explicitly building data for).

### R2-08: Times are integer minutes from midnight on a 15-minute grid

**Decision**: `day_of_week` is `0`–`6` (Monday = 0), `start_minute` and `end_minute` are integers in
`0`–`1440`, both multiples of 15, with `start_minute < end_minute`. CHECK constraints carry all four
rules.

**Rationale**: SQLite has no genuine `TIME` type, and the project already learned that lesson for
datetimes (`db/base.py:utcnow`'s comment on naive-UTC). Integers make the two operations this feature
actually performs — overlap detection and "does this slot cover 17:00–20:00" for Epic-02 — plain
integer comparisons, with no parsing, no locale, and no timezone. `1440` is permitted as an end so a
range may finish at midnight; `start < end` then forbids a range that crosses it, which is what FR-027
requires. The 15-minute grid is FR-028; enforcing it in the database as well as in the schema means an
import or a CLI cannot introduce a 17:07 slot.

**Alternatives considered**: `TIME`-typed columns (SQLite stores them as text and comparison becomes
string comparison, which happens to work for `HH:MM` and breaks the moment anything writes `9:00`);
storing a bitmask of 96 quarter-hours per day (compact and overlap-free by construction, but
unreadable in a query, and it destroys the "six ranges" and exact-boundary semantics the UI edits).

### R2-09: "Last revised" lives on the subject's own row, not on the slot table

**Decision**: add `availability_updated_at` (nullable) to `coach_details` and to `player_profiles`.

**Rationale**: FR-030 lets a person clear their week, and FR-032 requires the revision date to be
visible wherever times are read. A cleared week has no slots, so a `MAX(updated_at)` over the slot
table cannot answer "when did this person last touch their availability", and a person who cleared
their week would read as never having set one. Both subject kinds already have exactly one row in a
table this feature is touching anyway, so the timestamp has a natural home and needs no third table.

**Alternatives considered**: an `availability_weeks` parent table holding the timestamp and the
discriminator (a table whose only column of substance is a timestamp, plus a second write on every
save); deriving from `audit_entries` (availability changes are not administrative actions and FR-023
does not require auditing them).

### R2-10: The whole week is replaced in one transaction; last complete save wins

**Decision**: `PUT` semantics — the service validates the entire submitted week, deletes every
existing slot for that subject, inserts the new set, and stamps `availability_updated_at`, all inside
the request's single transaction. No version token, no optimistic concurrency check.

**Rationale**: FR-029 requires that no week is ever half-saved and FR-027 that a refused save leaves
the previous week exactly as it was; both fall out of validating before writing inside one
transaction. FR-010's edge case ("two devices save at once — the later complete save wins") is exactly
what SQLite's single-writer model gives for free, so adding the `StaleVersion` machinery feature 001
uses for profile edits would buy a conflict error the spec explicitly does not want. A week is a
statement of intent that the owner is overwriting wholesale, not a document two people co-edit.

**Alternatives considered**: PATCH-style per-slot add/remove endpoints (three round trips to move one
range, and a half-edited week is observable between them — a direct FR-029 violation); reusing the
`version` / `StaleVersion` pattern (contradicts the specified last-write-wins).

### R2-11: Availability endpoints hang off the resource that already owns authorization

**Decision**: a coach reads and writes their own week at `/me/availability`; a family reads and writes
a profile's week at `/me/players/{profile_id}/availability`, nested under the existing family resource;
a trainer reads at `/trainer/coaches/{coach_user_id}/availability` and
`/trainer/players/{player_profile_id}/availability`. There is no endpoint that takes a subject kind
plus an id.

**Rationale**: FR-033 and FR-036 are the whole security content of this half of the feature, and each
of these paths sits under a resource whose ownership check already exists and is already tested —
`family_router`'s `{profile_id}` routes resolve ownership through `FamilyService` (parent, or a
signed-in child for their own profile, with sibling isolation), and `trainer_router`'s routes are
scoped to the caller's own associations with no parameter that could widen them. A single
`/availability?subject_kind=&subject_id=` endpoint would move that entire authorization matrix into
new code, which is how a data-isolation bug gets written.

**Alternatives considered**: one polymorphic endpoint (above); putting the family's availability under
`/me/availability?player_profile_id=` (a query parameter that selects whose data you get is the shape
feature 001's R-25 already rejected for training context).

### R2-12: The summary string is formatted on the frontend; the API returns structured slots

**Decision**: every availability payload — own, family, and both trainer-side reads, including the
slots embedded in roster rows — carries the structured slot list plus
`availability_updated_at`. "Best times: Mon 5–8pm, Wed 6–9pm" is produced by one formatter in
`frontend/src/entities/availability/model/format-summary.ts`, used by both the summary line and the
full-week view.

**Rationale**: the frontend needs a formatter regardless, for the editor and the full week; adding a
second implementation server-side to produce a pre-baked string would mean two formatters that must
agree, in two languages, and would put presentation decisions (12-hour clock, day abbreviations, the
en-dash) in the service layer. The payload cost is bounded and small: FR-028 caps a person at six
ranges a day, so a subject is at most 42 slots of three integers, and a 25-row roster page carries at
most 1,050 such triples in the worst case that no real roster approaches.

**Alternatives considered**: a server-computed `availability_summary: str` on every row (two
formatters, or a formatter in the wrong layer); omitting availability from roster rows entirely and
requiring one request per row (FR-020 wants the summary *in* the list, and 25 extra requests per page
is worse than 25 embedded lists).

### R2-13: Availability's lifecycle hooks into three existing services

**Decision**: FR-039's four rules are implemented where the event already happens, not by a scheduled
sweep: `FamilyService.remove_profile` deletes that profile's slots; ending a coach assignment (R2-04)
leaves slots untouched; the trainer-side read filters on a live Active association, so disclosure ends
the moment an association does, with no separate step; and `ErasureService` deletes the erased
account's slots alongside the personal data it already removes.

**Rationale**: each of these is a one-line addition at a site that already runs in the right
transaction, and it keeps "the profile is gone but its times are still queryable" from ever existing as
a state. Availability is not personal information in the GDPR sense the erasure record protects, but
it is data belonging to a person who asked to be erased, and no requirement asks to retain it.

---

## Part C — Impersonation (US-01.07, FR-040 – FR-056)

### R2-14: One session, one substitution point — a `Principal` resolved by one dependency

**Decision**: impersonation does **not** create a second session or a second authentication path. The
admin's existing `sessions` row gains a nullable `impersonation_id`. The current
`get_current_user` dependency is refactored into `get_principal`, which resolves a frozen
`Principal(effective_user, real_user, impersonation)`; `get_current_user` becomes a one-line wrapper
returning `principal.effective_user`, and a second wrapper `get_impersonation_context` returns the
impersonation half. FastAPI caches a dependency per request, so both wrappers share one resolution and
one set of queries.

**Rationale**: FR-043 requires that everything the admin sees and can do while impersonating is
*exactly* what the impersonated person sees and can do. Substituting the effective user at the one
place every endpoint already gets its caller delivers that for the entire existing API — all eight
routers, every role gate, every context resolution, every ownership check — with no per-endpoint work
and no possibility that an endpoint written in Epic-02 forgets to honour impersonation. The
alternative shape, where endpoints learn about impersonation individually, makes FR-043 a promise that
every future endpoint must remember to keep.

Keeping one session row also gives FR-049 and FR-045 for free: the impersonated person's own sessions
are never touched because none are created or read, and exiting is a single column write with no
re-authentication.

**Alternatives considered**: issuing a second session token for the target (two live credentials for
one browser, and the impersonated person's session table now contains rows they did not create — a
support tool that pollutes the thing it is inspecting); a signed header or query parameter carrying
"act as" (unauthenticated state in a client-controlled channel).

### R2-15: The exit route is the one route that must not go through the effective user

**Decision**: `DELETE /admin/impersonations/current` authorizes on `Principal.real_user` — an Active
Super Admin holding an open impersonation — and not on `require_roles(SUPER_ADMIN)`. Every other
`/admin` route keeps its existing effective-user role gate.

**Rationale**: this is the one deliberate exception R2-14's substitution creates, and stating it
explicitly is what keeps it from being discovered as a bug. While impersonating a Trainer, the
effective user is a Trainer, so a Super Admin role gate would refuse the exit and lock the admin
inside the impersonation until the one-hour timeout. Symmetrically, the substitution is what makes
FR-047's other three prohibitions structural rather than hand-written: starting a nested
impersonation, deactivating, and erasing all sit behind Super Admin gates that the effective user
fails. Each still gets an explicit test, because "currently unreachable" and "forbidden" are different
claims and only the second one holds after Epic-07 adds more admin surface.

### R2-16: Dual attribution — one column on `audit_entries`, carried by the request's own session

**Decision**: `audit_entries` gains `impersonator_user_id` (nullable FK `users.id`). `get_principal`
stamps `db_session.info["impersonator_user_id"]` when an impersonation is live, and
`AuditRepository.add` — the single writer of that table — reads it into the new column. No service
signature changes.

**Rationale**: FR-052 requires that *every* change made during an impersonation names both parties.
Audit writes originate in a dozen services, each already receiving `actor_user_id` as a method
argument from its router. Threading a second identity through all of them would touch every audit
call site in the codebase to serve a case none of them can reason about, and every future service
would have to remember to pass it. The alternative used here puts the value on the object that is
already request-scoped, already injected everywhere through `Depends`, and already the thing the
repository holds — and reads it in exactly one function.

This is a deliberate, narrow deviation from the letter of Principle III's "dependencies MUST be
supplied through FastAPI `Depends`", and it is recorded in `plan.md`'s Complexity Tracking. It is not
a deviation from the rule that matters: `AsyncSession.info` is per-request state on an injected
object, not module-level or global mutable state, so nothing here can leak between concurrent
requests.

**Alternatives considered**: an `impersonator_user_id` parameter on `AuditRepository.add` and on every
audit-writing service method (~15 signatures changed for one feature's benefit, and silently wrong
whenever a future author omits it); recording the admin in the free-text `detail` column (unqueryable,
so "what did this admin change while impersonating" needs a `LIKE` scan); writing a second audit row
per action (doubles the table and makes "how many things happened" ambiguous).

### R2-17: `audit_entries` must be altered with plain `ADD COLUMN`, never `batch_alter_table`

**Decision**: revision 0011 adds the column with `op.add_column("audit_entries", ...)`. It must not
use `op.batch_alter_table` on that table, and the revision carries a comment saying why.

**Rationale**: this is a genuine trap, not a style preference. Alembic's batch mode on SQLite
implements an ALTER by creating a new table, copying rows, dropping the original, and renaming — and
dropping a table drops the triggers attached to it. Revision 0004's
`trg_audit_entries_no_update` / `trg_audit_entries_no_delete` are the defence-in-depth that makes
feature 001's FR-055 true against a script that bypasses the repository; a batch-mode ALTER would
delete them silently, leaving a passing test suite and an unprotected table. SQLite supports
`ALTER TABLE ... ADD COLUMN` natively for a nullable column with no default, so batch mode is not
needed here at all. The same caution applies to the new `impersonation_sessions` table, which gets its
own pair of triggers.

### R2-18: The history is its own append-only table and outlives the accounts it names

**Decision**: `impersonation_sessions` holds one row per impersonation — `admin_user_id`,
`target_user_id`, `auth_session_id`, `started_at`, `expires_at`, `ended_at`, `end_reason` — and gets
the same two SQLite triggers as `audit_entries`. `auth_session_id` is a plain `String(36)` with **no**
foreign key. Duration is derived, never stored.

**Rationale**: FR-055 requires that nothing can alter or remove an entry and that entries survive the
erasure of the impersonated account. A no-FK session reference follows `SignInAttempt`'s existing
precedent — the row must outlive the thing it points at, and a session row is deletable in a way an
audit fact must not be. Erasure survival needs nothing special: erasure anonymizes the `users` row
rather than deleting it, so the FKs to both participants stay valid and the history renders the
account by identifier once its personal details are gone. Duration is `ended_at - started_at`, and
storing a value derivable from two columns in the same row is how the two disagree later.

### R2-19: End-of-impersonation is enforced at request time, with six reasons

**Decision**: `get_principal` is where an impersonation ends. On every request carrying an open
impersonation it checks, in order: the one-hour deadline (`timed_out`), the target having been erased
(`target_erased`), and the target having left Active status **when it was Active at the start**
(`target_deactivated`). The other three reasons are written by their own actions: `exited` by the exit
route, `signed_out` by sign-out, `superseded` by starting a new impersonation while one is open.

**Rationale**: the project has no scheduler, so a deadline that is not enforced on read is not
enforced at all; this is the same choice `SessionRepository.is_usable` already makes for session
expiry. Handling it in the resolver means the very first request after the hour elapses is already the
admin's own, which is what FR-046 asks for.

The status condition resolves an apparent tension between FR-042 and FR-050 without narrowing either.
FR-042 permits impersonating an Inactive account; FR-050 ends a session when the target "leaves Active
status". Read literally, *leaving* Active requires having been Active, so an impersonation that began
on an Inactive account is not ended by that account still being Inactive — and one that began on an
Active account ends the moment someone deactivates it. Recording `status_at_start` on the
impersonation row makes that literal reading computable rather than a judgement call at each request.

**Alternatives considered**: a background expiry job (no scheduler exists, and it would leave a window
in which an expired impersonation still works); ending on any non-Active status regardless of the
starting status (would make FR-042's permission useless, since the session would end on the next
request); a client-side timer (trivially bypassed).

### R2-20: The admin is told why an impersonation ended, with no new server-side state

**Decision**: `GET /auth/session` gains two nullable blocks: `impersonation` (the live one, naming the
target and the deadline — this is what the banner renders) and `impersonation_ended`, populated when
the caller's most recent impersonation ended within the last 120 seconds for any reason other than
`exited`. The frontend shows a toast once per impersonation id, deduplicated in a small Zustand UI
slice.

**Rationale**: FR-046 requires that a timed-out admin be *told* why they are back in their own view.
The information exists in the row that was just closed, so a bounded look-back window turns it into a
derivable field rather than a "notice delivered" flag that needs its own write, its own migration, and
its own cleanup. `exited` is excluded because the admin who clicked Exit does not need to be told they
clicked Exit. Deduplication belongs on the client because "have I shown this toast" is client UI
state, which is precisely what the constitution reserves Zustand for.

**Alternatives considered**: a `notice_seen_at` column (a write on read, on the append-only table);
an HTTP header on the boundary response (invisible to a TanStack Query cache consumer, and lost on any
refetch); saying nothing (FR-046 requires it).

---

## Part D — Cross-cutting

### R2-21: Two new settings, one new rules module, no new dependency

**Decision**: `Settings` gains `coach_invitation_ttl_days: int` and `impersonation_max_minutes: int`,
both required with no default, added to `.env.example` alongside the existing `invitation_ttl_hours`.
The availability invariants — 15-minute grid, 6 ranges per day, 7 days, minutes-per-day bounds — go in
a new `app/core/availability_rules.py` as module constants, following `app/core/family_rules.py`'s
precedent. No package is added to either `pyproject.toml` or `package.json`.

**Rationale**: the two settings are deployment policy the client may want to change (a trainer asking
for 14-day invitations is a configuration conversation, not a code change), and the constitution
requires every configurable value to come from the environment through `pydantic-settings` with no
production-wrong default. The availability numbers are the opposite: they are domain invariants that
the database CHECK constraints and the Zod schema must agree on, and a value that must match a
migration is not configuration.

### R2-22: Contract version 1.3.0 — additive, with two documented field additions

**Decision**: `contracts/openapi.yaml` in this feature carries only the new and changed operations,
declared as version **1.3.0** of the same `/api/v1` contract feature 001 defined at 1.2.0. Two existing
response models gain fields: `CurrentUser` gains `impersonation` and `impersonation_ended`, and
`TrainerPlayerSummary` gains `availability` and `availability_updated_at`. No existing field changes
type or meaning, and no operation is removed.

**Rationale**: 1.2.0 contained breaking changes and said so, made "once while this repository's own
frontend is the only consumer". This feature needs no such licence — everything it adds is additive,
so a MINOR bump is the honest label and the existing frontend keeps compiling until it chooses to read
the new fields.

---

## Summary of decisions

| ID | Decision |
|---|---|
| R2-01 | Coach invitations get a dedicated table; the forward-declared `ShareLinkKind` value is dropped |
| R2-02 | Hashed single-use token, 7-day expiry, resend by supersession (mirrors `credential_setup_invitations`) |
| R2-03 | Four stored states; expiry derived; `blocked` is an annotation on a still-live invitation |
| R2-04 | The one-trainer assignment is `trainer_user_id` + `joined_at` on `coach_details` |
| R2-05 | Acceptance reuses the join flow's preview/register/accept shape and its per-IP throttle |
| R2-06 | Coach portal branding resolves the assigned trainer's, closing an existing TODO |
| R2-07 | One `availability_slots` table, two nullable owner FKs, exactly-one CHECK |
| R2-08 | Integer minutes from midnight on a 15-minute grid, `0`–`1440`, `start < end` |
| R2-09 | `availability_updated_at` lives on `coach_details` and `player_profiles` |
| R2-10 | Whole-week atomic replace in one transaction; last complete save wins; no version token |
| R2-11 | Endpoints nest under the resource whose ownership check already exists |
| R2-12 | Structured slots over the wire; one summary formatter, on the frontend |
| R2-13 | Availability lifecycle hooks into profile removal, association end, and erasure |
| R2-14 | One session; `Principal` substitutes the effective user at a single dependency |
| R2-15 | The exit route authorizes on the real user, not the effective one |
| R2-16 | `impersonator_user_id` column on `audit_entries`, carried via `AsyncSession.info` |
| R2-17 | `audit_entries` altered with plain `ADD COLUMN` — batch mode would silently drop its triggers |
| R2-18 | `impersonation_sessions` is append-only, trigger-protected, no FK to `sessions`, duration derived |
| R2-19 | Impersonation ends at request time; six reasons; `status_at_start` resolves FR-042 against FR-050 |
| R2-20 | End-reason notice derived from a 120-second look-back; client-side dedupe |
| R2-21 | Two new required settings; availability invariants as module constants; no new dependency |
| R2-22 | Contract 1.3.0, additive only |
