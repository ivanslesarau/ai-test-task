# Phase 1 Data Model: Coach Invitations, Availability & Impersonation

**Feature**: `002-coach-availability-impersonation` | **Date**: 2026-08-28

**Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

**Section numbering**: sections are numbered from **§101** so that a source comment citing
`data-model.md §103` cannot be confused with feature 001's document, whose sections run §1 – §33.

**Scope of change**: three new tables, two new columns on `coach_details`, one on `player_profiles`,
one on `sessions`, one on `audit_entries`, one enum removed, three enums added — all in a single
additive Alembic revision **0011** (§110). No existing column changes type, nullability, or meaning,
and no data is migrated.

---

## §101 — `coach_invitations` (new)

One trainer's offer to one address to become a coach on their roster (FR-001 – FR-019). A dedicated
table rather than a `share_links` kind, for the four reasons in research.md R2-01.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `String(36)` PK | no | UUIDv4, `default=new_uuid` |
| `trainer_user_id` | `String(36)` FK `users.id` ON DELETE CASCADE | no | Indexed. The roster the invitation admits to |
| `created_by_user_id` | `String(36)` FK `users.id` | no | The trainer today; a Super Admin acting in support later, without a schema change |
| `token_hash` | `String(64)` | no | SHA-256 of the mailed token, `unique=True`, indexed. The raw token exists only in the emailed URL (R2-02) |
| `invited_email` | `String(320)` | no | Lower-cased at the service boundary, as every other email in this codebase is. Indexed with `trainer_user_id` |
| `invitee_name` | `String(200)` | yes | FR-001's optional name. `null`, never `""` (Principle VI) |
| `message` | `String(2000)` | yes | FR-001's optional personal message. `null`, never `""` |
| `state` | `String` | no | `CoachInvitationState`, CHECK-constrained. Only the four event-driven values (§109.1, R2-03) |
| `issued_at` | `datetime` | no | `default=utcnow` |
| `expires_at` | `datetime` | no | `issued_at + settings.coach_invitation_ttl_days` (7). Indexed with `state` |
| `accepted_by_user_id` | `String(36)` FK `users.id` | yes | Set once, with `state = accepted`. The permanent record of which coach this invitation admitted |
| `accepted_at` | `datetime` | yes | Set together with the above |
| `revoked_at` | `datetime` | yes | Set with `state = revoked` (FR-006) |
| `superseded_at` | `datetime` | yes | Set with `state = superseded` by a resend (FR-005, R2-02) |
| `superseded_by_id` | `String(36)` FK `coach_invitations.id` | yes | The replacement row, so a resend chain is followable |
| `blocked_at` | `datetime` | yes | A refused acceptance under FR-014/FR-015. **Not** a state — the row stays `awaiting` (R2-03) |
| `blocked_reason` | `String` | yes | `CoachInvitationBlockReason` (§109.2), CHECK-constrained. Cleared on a later successful acceptance |

**Constraints**

- `ck_coach_invitations_state`: `state IN ('awaiting','accepted','revoked','superseded')`
- `ck_coach_invitations_block_reason`:
  `blocked_reason IS NULL OR blocked_reason IN ('role_not_coach','already_assigned')`
- `ck_coach_invitations_blocked_pair`: `(blocked_at IS NULL) = (blocked_reason IS NULL)` — a block has
  both halves or neither
- `ck_coach_invitations_accepted_pair`: `(accepted_at IS NULL) = (accepted_by_user_id IS NULL)`
- `ck_coach_invitations_terminal_pair`: `state <> 'accepted' OR accepted_at IS NOT NULL` — an accepted
  row always says who and when

**Indexes**

- `ix_coach_invitations_trainer_state` on `(trainer_user_id, state)` — the trainer's list view (FR-004)
- `uq_coach_invitations_token_hash` — unique lookup on acceptance
- `ix_coach_invitations_trainer_email` on `(trainer_user_id, invited_email)` — FR-007's duplicate guard

**Deliberately not a unique index**: `(trainer_user_id, invited_email)` is *not* unique. A trainer may
legitimately hold several rows for one address over time — one accepted, one superseded, one revoked.
FR-007's rule is narrower than uniqueness ("no second row that is presently *awaiting and unexpired*")
and is enforced in the service, which is also where the 409 body naming the existing invitation is
built. A partial unique index could express it, but it cannot produce that response body, and having
both would mean two places to change when the rule moves.

### §101.1 — Presented state (the one derivation)

`state` is what happened; what the trainer *sees* is computed by a single pure function
(`CoachInvitationService.presented_state`, mirrored by one frontend helper), with this precedence:

| Order | Presented | Condition |
|---|---|---|
| 1 | `accepted` | `state = accepted` |
| 2 | `revoked` | `state = revoked` |
| 3 | `superseded` | `state = superseded` — never listed to the trainer (FR-005: one invitation per address, not two) |
| 4 | `expired` | `state = awaiting AND expires_at <= now` |
| 5 | `blocked` | `state = awaiting AND blocked_at IS NOT NULL` |
| 6 | `awaiting` | otherwise |

Expired outranks blocked because an expired invitation cannot be accepted whatever the block said, and
the trainer's next action differs: resend, not wait.

### §101.2 — Usability predicate

One function, `CoachInvitationRepository.is_usable(row, now=None)`, mirroring
`ShareLinkRepository.is_usable`:

```
state == 'awaiting' AND expires_at > now
```

`blocked_at` deliberately does **not** appear: FR-015 requires that a refused acceptance not spend the
invitation, so a blocked row stays usable and clears its block on a later success.

---

## §102 — `coach_details` (extended)

Two columns added. They are what makes "a coach works for at most one trainer" true by construction
rather than by a checked rule (research.md R2-04).

| Column | Type | Null | Notes |
|---|---|---|---|
| `trainer_user_id` | `String(36)` FK `users.id` | yes | The assigned trainer. `NULL` = on no roster (FR-021, FR-022). Indexed for the roster query |
| `joined_at` | `datetime` | yes | When the coach accepted (FR-017). `NULL` exactly when `trainer_user_id` is `NULL` |
| `availability_updated_at` | `datetime` | yes | See §104 |

**Constraint**: `ck_coach_details_assignment_pair`:
`(trainer_user_id IS NULL) = (joined_at IS NULL)`.

**Index**: `ix_coach_details_trainer` on `trainer_user_id` — the trainer's roster (FR-020).

**No ON DELETE CASCADE on `trainer_user_id`**: accounts are never hard-deleted in this platform
(erasure anonymizes the row, feature 001 FR-049), so a cascade would encode a deletion that cannot
happen. The column is plain nullable with no cascade, and ending an assignment is an explicit service
action that writes the audit entry FR-023 requires.

---

## §103 — `availability_slots` (new)

One stated range of one day of one person's week (FR-024 – FR-032). One table serving both owner kinds
(research.md R2-07), times as integer minutes on a 15-minute grid (R2-08).

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `String(36)` PK | no | UUIDv4 |
| `coach_user_id` | `String(36)` FK `users.id` ON DELETE CASCADE | yes | Set for a coach's week |
| `player_profile_id` | `String(36)` FK `player_profiles.id` ON DELETE CASCADE | yes | Set for a player profile's week |
| `day_of_week` | `Integer` | no | `0` = Monday … `6` = Sunday |
| `start_minute` | `Integer` | no | Minutes from midnight, multiple of 15, `0` – `1425` |
| `end_minute` | `Integer` | no | Minutes from midnight, multiple of 15, `15` – `1440` |
| `created_at` | `datetime` | no | `default=utcnow`. Per-row provenance only; the week's revision date lives on the owner (§104) |

**Constraints**

- `ck_availability_slots_one_owner`:
  `(coach_user_id IS NULL) <> (player_profile_id IS NULL)` — exactly one owner
- `ck_availability_slots_day`: `day_of_week BETWEEN 0 AND 6`
- `ck_availability_slots_order`: `start_minute < end_minute`
- `ck_availability_slots_bounds`: `start_minute >= 0 AND end_minute <= 1440`
- `ck_availability_slots_grid`: `start_minute % 15 = 0 AND end_minute % 15 = 0`

**Indexes**

- `ix_availability_slots_coach_day` on `(coach_user_id, day_of_week)`
- `ix_availability_slots_profile_day` on `(player_profile_id, day_of_week)`

Both are what Epic-02's future "who is available Monday 5–8pm" query will read; this feature's own
reads are always the whole week for one owner.

**Not enforced in the database**: the six-ranges-per-day ceiling (FR-028) and the no-overlap rule
(FR-027). Both are properties of a *set* of rows, which a SQLite CHECK cannot express, so both live in
the service's whole-week validator (§111) — the same place FR-027's day-naming error message is built.
The single-row invariants above are duplicated in the database precisely because they *can* be, so no
import, seed, or CLI path can introduce a 17:07 slot.

---

## §104 — `availability_updated_at` (extended: `coach_details`, `player_profiles`)

| Table | Column | Type | Null | Notes |
|---|---|---|---|---|
| `coach_details` | `availability_updated_at` | `datetime` | yes | `NULL` = never stated (FR-035's "no times set") |
| `player_profiles` | `availability_updated_at` | `datetime` | yes | Same, per profile |

Written on every accepted save **and on a clear** (FR-030), which is why the timestamp cannot be
derived from the slot rows: a cleared week has none (research.md R2-09).

`NULL` is therefore "never stated" and a non-`NULL` value with zero slots is "cleared on that date" —
two distinct facts the trainer-side view distinguishes, and neither of which is "unavailable" (FR-035).

---

## §105 — `impersonation_sessions` (new)

One occasion on which a Super Admin viewed the platform as another person (FR-040 – FR-056).
Append-only, trigger-protected, and outliving both the session it rode on and the erasure of the
account it names (research.md R2-18).

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `String(36)` PK | no | UUIDv4 |
| `admin_user_id` | `String(36)` FK `users.id` | no | The Super Admin who started it. Indexed |
| `target_user_id` | `String(36)` FK `users.id` | no | The impersonated account. Indexed |
| `auth_session_id` | `String(36)` | yes | The admin's `sessions.id` at the time. **No foreign key**, deliberately (below) |
| `target_status_at_start` | `String` | no | `AccountStatus` value, CHECK-constrained. What makes FR-050's "leaves Active status" computable (R2-19) |
| `started_at` | `datetime` | no | `default=utcnow`. Indexed |
| `expires_at` | `datetime` | no | `started_at + settings.impersonation_max_minutes` (60). The one-hour ceiling (FR-046) |
| `ended_at` | `datetime` | yes | `NULL` = in progress (FR-053 renders these as in-progress) |
| `end_reason` | `String` | yes | `ImpersonationEndReason` (§109.3), CHECK-constrained. `NULL` exactly when `ended_at` is |

**Constraints**

- `ck_impersonation_sessions_end_pair`: `(ended_at IS NULL) = (end_reason IS NULL)`
- `ck_impersonation_sessions_end_reason`: `end_reason IS NULL OR end_reason IN (...)` (§109.3)
- `ck_impersonation_sessions_status_at_start`: `target_status_at_start IN ('active','inactive')` —
  `deleted` is refused before a row is ever written (FR-042)
- `ck_impersonation_sessions_not_self`: `admin_user_id <> target_user_id` (FR-042)
- `ck_impersonation_sessions_order`: `ended_at IS NULL OR ended_at >= started_at`

**Indexes**

- `ix_impersonation_sessions_admin` on `(admin_user_id, started_at)` — FR-054's filter by admin, and
  the "does this admin hold an open one" check (FR-048)
- `ix_impersonation_sessions_target` on `(target_user_id, started_at)` — FR-054's filter by person, and
  SC-017's "was this account ever impersonated"
- `ix_impersonation_sessions_open` on `admin_user_id`, partial `WHERE ended_at IS NULL` — at most one
  open row per admin

**Triggers** (revision 0011, same shape as revision 0004's on `audit_entries`):
`trg_impersonation_sessions_no_delete` on `BEFORE DELETE`, and
`trg_impersonation_sessions_no_update_closed` on `BEFORE UPDATE`, which aborts unless the update is the
one legitimate mutation — closing an open row:

```sql
CREATE TRIGGER trg_impersonation_sessions_no_update_closed
BEFORE UPDATE ON impersonation_sessions
WHEN OLD.ended_at IS NOT NULL
   OR NEW.started_at <> OLD.started_at
   OR NEW.admin_user_id <> OLD.admin_user_id
   OR NEW.target_user_id <> OLD.target_user_id
BEGIN
    SELECT RAISE(ABORT, 'impersonation_sessions is append-only: only closing an open row is allowed');
END;
```

This is stricter than a blanket no-UPDATE trigger would allow and stronger than none: a row can be
closed exactly once, and no closed row, participant, or start time can ever be rewritten — which is
what FR-055 requires of the history.

**Why `auth_session_id` carries no foreign key**: a `sessions` row is deletable and short-lived
(`ON DELETE CASCADE` from `users`), while this row must survive forever. The same reasoning already
governs `SignInAttempt`, which deliberately has no FK to `users`. The column is a breadcrumb for
support, not a join used by any query in this feature.

**Duration is not stored**: it is `ended_at - started_at`, computed in the response schema. Storing it
is how two columns in one row come to disagree.

---

## §106 — `sessions` (extended)

| Column | Type | Null | Notes |
|---|---|---|---|
| `impersonation_id` | `String(36)` FK `impersonation_sessions.id` | yes | The open impersonation this session is currently riding. `NULL` for every ordinary session |

This one nullable pointer is the whole live-state mechanism (research.md R2-14): it is set when an
impersonation starts, cleared when it ends for any of the six reasons, and read once per request by
`get_principal`. There is no second session row and no second credential.

**Invariant maintained by the service, not the schema**: a `sessions` row whose `impersonation_id` is
set always points at a row whose `ended_at IS NULL`. The resolver treats a pointer to a closed row as
"not impersonating" and clears it, so a crash between the two writes degrades to the safe reading
rather than to a stuck impersonation.

---

## §107 — `audit_entries` (extended)

| Column | Type | Null | Notes |
|---|---|---|---|
| `impersonator_user_id` | `String(36)` FK `users.id` | yes | The Super Admin who was acting as `actor_user_id` when this entry was written (FR-052). `NULL` for every ordinary action |

Written by `AuditRepository.add` from `AsyncSession.info["impersonator_user_id"]`, the single choke
point research.md R2-16 justifies. `actor_user_id` keeps its existing meaning — the account whose
capabilities were used — so every existing query, view, and test continues to mean what it meant, and
"who really did this" becomes answerable by reading one more column.

**Migration caution (research.md R2-17)**: this column MUST be added with plain
`op.add_column("audit_entries", ...)`. `op.batch_alter_table` on SQLite recreates the table, which
would silently drop revision 0004's two append-only triggers.

**Index**: `ix_audit_entries_impersonator` on `impersonator_user_id`, partial
`WHERE impersonator_user_id IS NOT NULL` — the compliance question is always "what did this admin
change while impersonating", never "what did nobody impersonate".

---

## §108 — Audit actions added

`audit_entries.action` is a free-text `String(50)`; these are the values this feature writes
(FR-023, FR-051, FR-052). `target_user_id` is the account the action concerns; `detail` carries the
invitation id or the reason where one applies.

| Action | Actor | Target | Written when |
|---|---|---|---|
| `coach_invitation_issued` | trainer | `NULL` (no account yet) | FR-001. `detail` carries the invitation id and the invited address |
| `coach_invitation_resent` | trainer | `NULL` | FR-005. `detail` names both the superseded and the new invitation |
| `coach_invitation_revoked` | trainer | `NULL` | FR-006 |
| `coach_invitation_accepted` | coach | coach | FR-017. `detail` names the trainer and the invitation |
| `coach_invitation_refused` | coach (or `NULL` for an unauthenticated attempt) | `NULL` | FR-014, FR-015. `detail` carries the block reason, never the other trainer's identity |
| `coach_assignment_ended` | trainer | coach | FR-021 |
| `impersonation_started` | admin | impersonated | FR-051. Paired with the `impersonation_sessions` row |
| `impersonation_ended` | admin | impersonated | FR-051. `detail` carries the end reason |

The two impersonation actions are recorded in the audit trail *as well as* in
`impersonation_sessions`, and this duplication is deliberate: the audit trail is what a Super Admin
already reads per account (`GET /admin/users/{id}/audit`), so "was I ever impersonated" is answerable
there too, while the history table is what FR-053's report and FR-055's tamper-proofing need.

---

## §109 — Enums

New members of `app/models/enums.py`, all `StrEnum`, all persisted as their string value with a
matching CHECK constraint — the pattern every existing enum in that module follows.

### §109.1 `CoachInvitationState`

```
AWAITING = "awaiting"        # live and usable until expires_at
ACCEPTED = "accepted"        # terminal; a coach joined
REVOKED = "revoked"          # terminal; the trainer withdrew it
SUPERSEDED = "superseded"    # terminal; replaced by a resend
```

`expired` and `blocked` are absent by design (§101.1, research.md R2-03).

Permitted transitions (a `frozenset` plus an `is_transition_allowed` helper, exactly as
`ALLOWED_STATUS_TRANSITIONS` and `ALLOWED_APPROVAL_TRANSITIONS` are shaped):

| From | To | Trigger |
|---|---|---|
| `awaiting` | `accepted` | a valid acceptance (FR-017, FR-018) |
| `awaiting` | `revoked` | the trainer revokes (FR-006) |
| `awaiting` | `superseded` | the trainer resends (FR-005) |

Nothing leaves a terminal state, and there is no `awaiting → awaiting` self-transition: setting or
clearing a block writes `blocked_at`/`blocked_reason` without touching `state`.

### §109.2 `CoachInvitationBlockReason`

```
ROLE_NOT_COACH = "role_not_coach"      # FR-014
ALREADY_ASSIGNED = "already_assigned"  # FR-015
```

Two values, because FR-019 requires the trainer to learn *that* the invitation could not be accepted
while learning nothing about the other trainer. The reason shown to the trainer is a fixed phrase per
value; the other trainer's name is never stored here and so cannot leak.

### §109.3 `ImpersonationEndReason`

```
EXITED = "exited"                          # the admin left it (FR-045)
TIMED_OUT = "timed_out"                    # the one-hour ceiling (FR-046)
SIGNED_OUT = "signed_out"                  # the admin signed out (FR-046)
SUPERSEDED = "superseded"                  # a new impersonation replaced it (FR-048)
TARGET_DEACTIVATED = "target_deactivated"  # FR-050, per R2-19's literal reading
TARGET_ERASED = "target_erased"            # FR-050
ADMIN_DEACTIVATED = "admin_deactivated"    # FR-050, the admin's own account
```

### §109.4 Removed

`ShareLinkKind.COACH_SINGLE_USE` is deleted (research.md R2-01). No row has ever carried the value —
`ShareLinkRepository.insert_standing_link` is the only writer of `share_links.kind` and it writes
`PLAYER_STANDING` unconditionally — so no data migration and no backfill is involved. The enum's
docstring, which currently promises this value to US-01.08, is corrected to record where coach
invitations actually live.

### §109.5 Not an enum: `day_of_week`

`day_of_week` is a plain `Integer` `0`–`6`, not a `StrEnum`. Ordering and arithmetic are the entire
point of the column — "the next available day", "sort the week" — and an integer with a CHECK gives
both plus a two-byte row. Day *names* are presentation, resolved by the frontend formatter
(research.md R2-12).

---

## §110 — Alembic revision 0011 (single revision, additive)

`0011_coach_invitations_availability_impersonation.py`, `down_revision = "0010"`.

**Upgrade, in order:**

1. `create_table("coach_invitations")` with every constraint and index in §101.
2. `create_table("availability_slots")` with every constraint and index in §103.
3. `create_table("impersonation_sessions")` with every constraint and index in §105, then
   `op.execute` the two triggers.
4. `op.add_column("coach_details", ...)` × 3 — `trainer_user_id`, `joined_at`,
   `availability_updated_at` — then the check constraint and index. `coach_details` carries no
   triggers, so batch mode is available if a constraint needs it; plain `add_column` suffices for the
   columns themselves.
5. `op.add_column("player_profiles", "availability_updated_at")`.
6. `op.add_column("sessions", "impersonation_id")`.
7. **`op.add_column("audit_entries", "impersonator_user_id")` — plain `add_column` only**, never
   `batch_alter_table` (research.md R2-17), followed by the partial index. The revision carries this
   warning as a comment, because the failure mode is a silently unprotected audit table with a green
   test suite.

**Downgrade**: drops the three tables (dropping the two triggers first), then the six added columns.
`audit_entries.impersonator_user_id` is dropped with plain `op.drop_column`, which SQLite has
supported natively since 3.35 — the same caution as the upgrade applies.

**Data**: none. Every added column is nullable, and every existing row is correct with `NULL` in all
of them: no coach has a trainer yet, nobody has stated times, no session is impersonating, and no
past audit entry was written under impersonation.

---

## §111 — Validation rules (service layer)

The rules that cannot live in a CHECK constraint, and where each one lives.

### §111.1 Coach invitations

| Rule | FR | Where |
|---|---|---|
| Invited address must be a valid email; stored lower-cased | FR-001 | Pydantic `EmailStr` on the request schema |
| `invitee_name` / `message`: `str \| None` with `min_length=1`, so `""` is a 422 | FR-001, Principle VI | Request schema |
| No second `awaiting`-and-unexpired invitation for the same `(trainer, address)` | FR-007 | `CoachInvitationService.issue`, raising a 409 that names the existing invitation |
| Issuing and resending refused unless the trainer's account is Active | FR-010 | `CoachInvitationService`, before any write |
| Acceptance refused unless the inviting trainer is still Active | FR-010 | `CoachInvitationService.resolve_usable`, one refusal path |
| The accepting account's email equals `invited_email` | FR-013 | `CoachInvitationService.accept`; the register path takes the address *from* the invitation, so it cannot mismatch |
| The accepting account's role is Coach | FR-014 | `accept`, writing `blocked_reason = role_not_coach` |
| The accepting coach has `coach_details.trainer_user_id IS NULL` | FR-015 | `accept`, writing `blocked_reason = already_assigned`, leaving the invitation usable |
| Acceptance by a coach already on *this* trainer's roster is a no-op that says so | FR-016 | `accept`, before the FR-015 branch |
| Exactly one of two concurrent acceptances wins | FR-018 | The `awaiting → accepted` transition guarded by a conditional UPDATE on `state`; the loser sees "already used" |
| Only the owning trainer, or a Super Admin, may read/resend/revoke | FR-009 | Router role gate plus an owner check in the service |

### §111.2 Availability (one whole-week validator)

`AvailabilityService.replace_week` validates the entire submitted week **before** touching a row, and
raises `ValidationFailure` with the offending day named (FR-027):

1. Every slot: `day_of_week` in `0..6`; `start_minute` and `end_minute` on the 15-minute grid;
   `0 <= start_minute < end_minute <= 1440`.
2. Per day: at most `MAX_SLOTS_PER_DAY` (6) slots (FR-028).
3. Per day: no two slots overlap. Slots are sorted by `start_minute`; an overlap is
   `next.start_minute < previous.end_minute`. Touching ranges (`next.start == previous.end`) are
   **valid** (FR-027, explicit in the spec's edge cases).
4. Only then: delete every existing slot for the owner, insert the new set, stamp
   `availability_updated_at` — one transaction (FR-029, research.md R2-10).

The same three rules are encoded once more in the frontend's Zod schema (Principle II boundary parity),
and the constants they read come from one module on each side (research.md R2-21).

### §111.3 Impersonation

| Rule | FR | Where |
|---|---|---|
| Caller is an Active Super Admin | FR-041 | `require_roles(SUPER_ADMIN)` on the start route — enforced on the request |
| Target is not a Super Admin, not the caller, not erased | FR-042 | `ImpersonationService.start` |
| Target may be Active or Inactive; Inactive is labelled | FR-042 | `start` records `target_status_at_start` and the response carries it |
| At most one open impersonation per admin; starting closes the previous as `superseded` | FR-048 | `start`, inside one transaction |
| Exit authorizes on the **real** user, not the effective one | FR-045, R2-15 | The exit route's own dependency |
| One-hour ceiling; ends on the first request after the deadline | FR-046 | `get_principal` |
| Ends on target erasure, on the target leaving Active when it started Active, and on the admin leaving Active | FR-050, R2-19 | `get_principal` |
| Nested impersonation, credential change, deactivate, erase all refused while impersonating | FR-047 | Structural: the effective user fails those gates (R2-15) — with an explicit test each |
| History is Super-Admin-only | FR-056 | Router role gate |
| No entry can be altered or removed | FR-055 | Repository exposes insert/close/select only, plus the §105 triggers |

---

## §112 — Entity relationships

```
users (trainer) ──1:N──> coach_invitations ──0:1──> users (coach, accepted_by)
                                │
                                └──0:1──> coach_invitations (superseded_by)

users (coach) ──1:1──> coach_details ──0:1──> users (trainer_user_id)
                            │
                            └── availability_updated_at

users (coach) ──1:N──> availability_slots <──N:1── player_profiles
                       (exactly one owner per row)

users (admin) ──1:N──> impersonation_sessions ──N:1──> users (target)
                              ^
                              └──0:1── sessions.impersonation_id (the live pointer)

audit_entries.actor_user_id        = whose capabilities were used
audit_entries.impersonator_user_id = who was really acting, when impersonating
```

---

## §113 — Query patterns

| Query | Shape | Index used |
|---|---|---|
| Trainer's invitation list (FR-004) | `WHERE trainer_user_id = ? AND state <> 'superseded'` ordered by `issued_at DESC`, paged | `ix_coach_invitations_trainer_state` |
| FR-007 duplicate guard | `WHERE trainer_user_id = ? AND invited_email = ? AND state = 'awaiting' AND expires_at > now` | `ix_coach_invitations_trainer_email` |
| Acceptance lookup | `WHERE token_hash = ?` | `uq_coach_invitations_token_hash` |
| Trainer's coach roster (FR-020) | `coach_details JOIN users` `WHERE coach_details.trainer_user_id = ?`, paged | `ix_coach_details_trainer` |
| One owner's week (FR-024, FR-025, FR-034) | `WHERE coach_user_id = ?` or `WHERE player_profile_id = ?` ordered by `(day_of_week, start_minute)` | either day index |
| Weeks for a roster page (FR-020, FR-034) | one `WHERE player_profile_id IN (...)` per page, never one query per row | `ix_availability_slots_profile_day` |
| Open impersonation for this admin (FR-048) | `WHERE admin_user_id = ? AND ended_at IS NULL` | `ix_impersonation_sessions_open` |
| Live impersonation for this request | `sessions.impersonation_id` → primary key fetch | PK |
| History, filtered (FR-053, FR-054) | `WHERE admin_user_id = ?` / `target_user_id = ?` / `started_at BETWEEN ? AND ?`, paged | admin / target index |
| "What did this admin change while impersonating" | `WHERE impersonator_user_id = ?` | `ix_audit_entries_impersonator` |

The roster read is the one N+1 risk in this feature, and it is closed by design: availability for a
page of coaches or players is fetched with a single `IN` query keyed by owner and grouped in the
service (research.md R2-12 bounds the payload at 42 slots per owner).

---

## §114 — Interaction with existing lifecycles

| Existing event | What this feature adds | FR |
|---|---|---|
| `FamilyService.remove_profile` (soft removal) | Delete that profile's `availability_slots` rows; leave `availability_updated_at` as the record that times once existed | FR-039 |
| Ending a coach assignment | `coach_details.trainer_user_id`/`joined_at` → `NULL`; slots untouched, so the coach keeps their week | FR-021, FR-039 |
| An association ending (`trainer_player_associations.status`) | Nothing to delete — the trainer-side read joins on an Active association, so disclosure stops immediately | FR-039 |
| `ErasureService.erase` | Delete the erased account's `availability_slots`; end any open impersonation of that account as `target_erased`; **keep** every `impersonation_sessions` row | FR-039, FR-050, FR-055 |
| `UserAdminService.deactivate` | End any open impersonation whose target this is (`target_deactivated`) or whose admin this is (`admin_deactivated`), in the same transaction as the status change and the existing session revocation | FR-050 |
| `AuthService.sign_out` | Close any open impersonation on that session as `signed_out` before revoking the session | FR-046 |
| `AuthService.authenticate_session` | Unchanged. Impersonation resolution happens one layer out, in `get_principal`, so the session rules stay exactly as feature 001 wrote them | R2-14 |
| `BrandingService.resolve_for_user` | The Coach branch resolves `coach_details.trainer_user_id`'s branding instead of returning the platform default | R2-06 |
