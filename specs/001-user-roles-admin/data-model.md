# Phase 1 Data Model: User Roles, Authorization & Super Admin User Management

**Feature**: `001-user-roles-admin` | **Date**: 2026-08-19

**Inputs**: [spec.md](./spec.md) Key Entities and FR-001 – FR-056, [research.md](./research.md) R-03,
R-08, R-10, R-15, R-16

All tables are SQLAlchemy 2.0 declarative models using `Mapped`/`mapped_column`, created only through
Alembic revisions. Times are stored as timezone-aware UTC timestamps. Identifiers are UUIDv4 stored
as 36-character text, chosen over autoincrementing integers so that an account identifier can appear
in an anonymized email address (R-08) without leaking how many accounts exist.

---

## 1. Enumerations

Both are Python `enum.StrEnum` and are persisted as constrained text rather than integers, so a raw
database read stays legible and a migration cannot silently reorder them.

### `UserRole`

| Value | Meaning |
|---|---|
| `super_admin` | Platform operator. Manages every account. Cannot be impersonated (impersonation is out of scope here). |
| `trainer` | Business owner running a training organization. |
| `coach` | Contractor delivering sessions. |
| `player_parent` | A family account — a player, a parent, or a parent who also trains. |

Exactly four values, closed set (FR-002). A fifth role is a schema change, not a data entry.

### `AccountStatus`

| Value | Sign-in permitted | Mutable | Meaning |
|---|---|---|---|
| `active` | Yes | Yes | Normal operating state. |
| `inactive` | No | Yes | Deactivated; all history preserved (FR-038). |
| `deleted` | No | No | Personal information erased; terminal (FR-048). |

Permitted transitions, enforced in the service layer and asserted by unit tests (FR-003):

```
active   ──deactivate──▶ inactive
inactive ──reactivate──▶ active
active   ───erase──────▶ deleted
inactive ───erase──────▶ deleted
deleted  ──────────────▶ (nothing — terminal)
```

Any other transition is a domain error, including `active → active` and `inactive → inactive`, which
covers the spec's edge case on deactivating an already inactive account.

---

## 2. `users`

The account: identity, credential, role, status. One row per person, for the life of the platform.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | text(36) | PK | UUIDv4. Never reused, never reassigned. |
| `email` | text(320) | not null, **unique**, indexed | Case-insensitively unique — stored lowercased and compared lowercased, so `Ann@x.com` cannot coexist with `ann@x.com`. Uniqueness spans every status (FR-004). |
| `password_hash` | text | **nullable** | Argon2id (R-04). `NULL` means no usable password yet — an invited account before first setup, or an erased account. Never returned by any query the API serializes. |
| `role` | text | not null, check in `UserRole` | Exactly one per account (FR-002). |
| `status` | text | not null, check in `AccountStatus`, indexed | Default `active`. |
| `last_login_at` | timestamptz | nullable | Set on each successful sign-in (FR-001). |
| `version` | integer | not null, default 1 | Optimistic concurrency counter (R-10). Incremented on every status change. |
| `created_at` | timestamptz | not null | Read-only in the profile (FR-033). |
| `updated_at` | timestamptz | not null | Maintained on update. |

**Indexes**: unique on `email`; composite on `(status, role)` for the directory's filters; on
`created_at` for its default ordering (FR-052).

**Why `password_hash` is nullable rather than a fifth status**: an invited trainer who has not yet
set a password holds an Active account — it appears in the directory as Active, it can be deactivated,
and it is Active in every business sense. What it lacks is a credential. Modelling that as a
"pending" status would put a state in the enum that FR-003's transition table has no place for, and
would force every status check in the codebase to ask "active *or* pending?". A nullable hash states
the actual fact: sign-in requires both an Active status and a usable credential, which FR-008 and
FR-026 together already say.

**Relationships**: one-to-one with `user_profiles` (required); one-to-one with each of the four role
detail tables (at most one, and only the one matching `role`); one-to-many with `sessions`,
`credential_setup_invitations`, and `sign_in_attempts`; referenced by `audit_entries` twice and by
`erasure_records` once.

---

## 3. `user_profiles`

Personal detail shared by every role (FR-005). Exactly one row per account, created in the same
transaction as the account so no account is ever profile-less.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `user_id` | text(36) | PK, FK → `users.id`, cascade delete | One-to-one. |
| `first_name` | text(100) | not null | Required (FR-005). Becomes `Deleted` on erasure. |
| `last_name` | text(100) | not null | Required. Becomes `User` on erasure. |
| `phone` | text(32) | nullable | E.164-normalized on save. Cleared on erasure (FR-045). |
| `photo_key` | text(128) | nullable | Opaque storage key, not a URL — the served URL is derived, so storage layout can change without a data migration. `NULL` renders the default avatar (FR-035). |
| `updated_at` | timestamptz | not null | |

Name is stored as two columns rather than one display string because US-01.11 lists first and last
name as separately editable fields.

---

## 4. Role detail tables

Four optional one-to-one extensions (R-15, FR-006). A row exists only when it matches the account's
role; the service layer creates the right one at account creation and rejects a mismatch. Each is
keyed by `user_id` so the relationship cannot be duplicated.

### 4.1 `trainer_organizations`

| Column | Type | Constraints |
|---|---|---|
| `user_id` | text(36) | PK, FK → `users.id`, cascade delete |
| `business_name` | text(200) | not null — required at creation (FR-021) |
| `address` | text(500) | nullable |
| `website` | text(500) | nullable — validated as an absolute http/https URL when present |
| `description` | text(2000) | nullable |

Later epics extend this table with billing identifiers, subscription status, and platform fee. Those
columns are **not** created now; Epic-01's data requirements list them explicitly as belonging to
Epic-05.

### 4.2 `coach_details`

| Column | Type | Constraints |
|---|---|---|
| `user_id` | text(36) | PK, FK → `users.id`, cascade delete |
| `bio` | text(2000) | nullable |
| `credentials` | text(1000) | nullable |
| `certifications` | text(1000) | nullable |
| `is_publicly_visible` | boolean | not null, default false |

The single-trainer assignment Epic-01 describes is **out of scope** and no column for it is created;
adding it later is an additive migration.

### 4.3 `player_details`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `user_id` | text(36) | PK, FK → `users.id`, cascade delete | |
| `school` | text(200) | nullable | Self-editable (FR-032) |
| `jersey_number` | text(10) | nullable | Text, not integer — jersey numbers carry leading zeros and are not arithmetic |
| `skill_level` | text(50) | nullable | **Never** writable through the profile API (FR-007, FR-033). No endpoint in this feature sets it; a later trainer-facing feature does. |

`skill_level` is deliberately a free-text column rather than an enum: Epic-01 open question Q-01.01
leaves the skill level vocabulary undecided, so constraining it now would need a migration once the
client answers.

### 4.4 `parent_contacts`

| Column | Type | Constraints |
|---|---|---|
| `user_id` | text(36) | PK, FK → `users.id`, cascade delete |
| `emergency_contact_name` | text(200) | nullable |
| `emergency_contact_phone` | text(32) | nullable |
| `emergency_contact_relation` | text(100) | nullable |

Attached to `player_parent` accounts alongside `player_details`, because Epic-01 describes one family
account that may both train and parent. Child profiles and parent-child links are out of scope.

---

## 5. `sessions`

An admitted person's continuing access (R-03, FR-011, FR-012).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | text(36) | PK | |
| `user_id` | text(36) | FK → `users.id`, cascade delete, indexed | |
| `token_hash` | text(64) | not null, unique, indexed | SHA-256 of the cookie value. The raw token is generated once, sent in the cookie, and never stored — a leaked database therefore yields no usable session. |
| `created_at` | timestamptz | not null | |
| `last_seen_at` | timestamptz | not null | Advanced on use; drives the sliding 7-day inactivity window. |
| `expires_at` | timestamptz | not null, indexed | Absolute ceiling, recomputed as `last_seen_at + 7 days`. |
| `revoked_at` | timestamptz | nullable | Set on sign-out and on any status change away from Active. |

A session authenticates only when `revoked_at` is null, `expires_at` is in the future, and the owning
account is Active. Deactivation and erasure revoke every session for the account **in the same
transaction** as the status change, which is what makes FR-012's "the moment" and SC-007's one-minute
ceiling true by construction rather than by a background job.

Expired and revoked rows are pruned by a maintenance routine; retaining them briefly is deliberate,
since a request arriving on a just-revoked session should be distinguishable from one arriving on a
token that never existed.

---

## 6. `credential_setup_invitations`

A single-use, time-limited permission to set a password (R-01, FR-025 – FR-028).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | text(36) | PK | |
| `user_id` | text(36) | FK → `users.id`, cascade delete, indexed | |
| `token_hash` | text(64) | not null, unique, indexed | SHA-256 of the link's secret. As with sessions, the secret exists only in the email. |
| `issued_by_user_id` | text(36) | FK → `users.id`, not null | The acting Super Admin. |
| `created_at` | timestamptz | not null | |
| `expires_at` | timestamptz | not null | `created_at + 24 hours`. |
| `consumed_at` | timestamptz | nullable | Set on first successful use; a second use fails (FR-027). |
| `superseded_at` | timestamptz | nullable | Set when a re-invitation is issued, invalidating this one (FR-028). |

An invitation is usable only when `consumed_at` and `superseded_at` are both null, `expires_at` is in
the future, **and** the owning account is Active — which covers the spec's edge case where an account
is deactivated before first sign-in.

---

## 7. `sign_in_attempts`

Durable failed-attempt records backing the rate limit (R-06, FR-013, SC-011).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | integer | PK autoincrement | High-volume, never externally referenced, so an integer key is right here. |
| `email` | text(320) | not null, indexed | Stored lowercased. Recorded even for an email that matches no account, since that is the case an attacker probes. |
| `client_ip` | text(45) | not null, indexed | IPv6-capable length. |
| `attempted_at` | timestamptz | not null, indexed | |
| `successful` | boolean | not null | Successful attempts are recorded too, so the window can be cleared on success. |

The limit is evaluated by counting unsuccessful rows in the trailing 15 minutes for the email and,
separately, for the client address; 10 or more in either dimension refuses the attempt. Because the
window slides, access resumes automatically without administrative action, as SC-011 requires. Rows
older than the retention period are pruned by the same maintenance routine that prunes sessions.

**Composite index** on `(email, attempted_at)` and on `(client_ip, attempted_at)` — the count query
is on the sign-in hot path and must not scan.

---

## 8. `audit_entries`

Append-only record of every administrative action (FR-054, FR-055, R-16).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | text(36) | PK | |
| `actor_user_id` | text(36) | FK → `users.id`, **nullable** | The acting account. Nullable only so that a `RESTRICT`-style constraint can never block an erasure; in practice always set for the actions in this feature. |
| `target_user_id` | text(36) | FK → `users.id`, nullable, indexed | The affected account. |
| `action` | text(50) | not null, indexed | `user_created`, `invitation_issued`, `invitation_consumed`, `user_deactivated`, `user_reactivated`, `user_erased`, `permission_denied`. |
| `reason` | text(1000) | nullable | Required by the service for `user_erased` (FR-044). |
| `detail` | text(2000) | nullable | Non-personal supporting context, e.g. the role assigned or the endpoint denied. |
| `occurred_at` | timestamptz | not null, indexed | |

The repository for this table exposes **insert and select only** — no update or delete method is
written. An Alembic revision additionally installs SQLite triggers that raise on `UPDATE` and
`DELETE` against the table, so the guarantee survives a future script that bypasses the repository.

`permission_denied` entries satisfy FR-020's requirement to record refused attempts. They carry the
action attempted and the role that attempted it, never the request body, so a denied request cannot
smuggle personal data into the audit trail.

**On the email address in audit entries**: `user_created` records the email in `detail`, as FR-029
requires. After that account is erased, the audit trail still holds it — which is consistent with the
erasure design, since FR-049 retains the original email in the compliance record anyway. Purging
audit history is out of scope and no retention policy is specified (see the spec's Assumptions).

---

## 9. `erasure_records`

The legally retained trace of one privacy erasure (FR-049, R-08).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | text(36) | PK | |
| `user_id` | text(36) | FK → `users.id`, not null, unique | Unique — an account can be erased once, because erasure is terminal. |
| `original_email` | text(320) | not null | The address before anonymization. |
| `original_first_name` | text(100) | not null | |
| `original_last_name` | text(100) | not null | |
| `erased_by_user_id` | text(36) | FK → `users.id`, not null | The acting Super Admin. |
| `reason` | text(1000) | not null | Captured at the moment of erasure (FR-044). |
| `erased_at` | timestamptz | not null | |

Reachable through exactly one Super-Admin-only endpoint and never joined into any account view, which
is how FR-049's "readable only by Super Admins" is realized. No repository method returns it alongside
account data.

---

## 10. The erasure transformation

FR-045 in concrete column terms. All of it happens in one transaction; either every line applies or
none does.

| Target | Before | After |
|---|---|---|
| `users.email` | `ann.lee@example.org` | `deleted_{users.id}@example.com` |
| `users.password_hash` | Argon2id hash | `NULL` |
| `users.status` | `active` or `inactive` | `deleted` |
| `users.version` | *n* | *n + 1* |
| `user_profiles.first_name` | `Ann` | `Deleted` |
| `user_profiles.last_name` | `Lee` | `User` |
| `user_profiles.phone` | `+15551234567` | `NULL` |
| `user_profiles.photo_key` | storage key | `NULL`, and both stored image files removed |
| `player_details.school` | `Lincoln High` | `NULL` |
| `player_details.jersey_number` | `07` | `NULL` |
| `player_details.skill_level` | `Intermediate` | **unchanged** — a classification, not an identifier, and reporting distributions depend on it |
| `parent_contacts.*` | emergency contact | all `NULL` |
| `coach_details.bio`, `credentials`, `certifications` | free text | `NULL` — free text written by the person may name them |
| `coach_details.is_publicly_visible` | either | `false` |
| `trainer_organizations.business_name` | `Lee Basketball` | **unchanged** — a business identity that later epics' revenue records attribute to; see the note below |
| `trainer_organizations.address`, `website`, `description` | free text | `NULL` |
| Every `sessions` row | possibly active | revoked |
| Every unconsumed invitation | possibly valid | superseded |

`example.com` is reserved by RFC 2606 and cannot receive mail, so the placeholder address is inert.
Deriving it from `users.id` makes it unique without a lookup, and because email uniqueness spans all
statuses, the former address is released for reuse exactly as FR-050 requires.

**Two judgement calls recorded here rather than buried in code:**

- `skill_level` and `business_name` survive erasure. A trainer's business name is the entity that
  Epic-05's revenue records and Epic-03's rosters attribute to; clearing it would make historical
  organizational reporting unreadable, which FR-047 forbids. Where a sole trader's business name *is*
  their personal name, this retains personal data — a real limitation, and the reason the spec flags
  legal review. If counsel rejects it, the fix is to anonymize `business_name` to
  `Deleted Organization` and accept the reporting loss; that is a one-line change to this table.
- Collision with a placeholder address is prevented at creation: the account-creation validator
  rejects any submitted email matching the `deleted_*@example.com` pattern, closing the spec's edge
  case on that collision.

---

## 11. Entity relationships

```
                        ┌─────────────────┐
                        │      users      │
                        │  id, email,     │
                        │  role, status,  │
                        │  password_hash  │
                        └────────┬────────┘
                                 │ 1
         ┌───────────────┬───────┴────────┬──────────────────┬─────────────────┐
         │ 1             │ 0..1           │ 0..*             │ 0..*            │ 0..1
┌────────▼───────┐  ┌────▼──────────┐ ┌───▼──────┐ ┌─────────▼──────────┐ ┌────▼──────────┐
│ user_profiles  │  │ role detail   │ │ sessions │ │ credential_setup_  │ │ erasure_      │
│ names, phone,  │  │ (exactly one  │ │          │ │ invitations        │ │ records       │
│ photo_key      │  │  of four,     │ └──────────┘ └────────────────────┘ └───────────────┘
└────────────────┘  │  matching     │
                    │  users.role)  │        ┌──────────────────┐   ┌────────────────────┐
                    │               │        │ audit_entries    │   │ sign_in_attempts   │
                    │ trainer_orgs  │        │ actor → users    │   │ keyed by email     │
                    │ coach_details │        │ target → users   │   │ and client_ip,     │
                    │ player_details│        │ append-only      │   │ no FK to users     │
                    │ parent_contacts│       └──────────────────┘   └────────────────────┘
                    └───────────────┘
```

`sign_in_attempts` deliberately holds **no foreign key** to `users`: attempts against a
non-existent email are the ones worth recording, and a foreign key would make them unrecordable.

---

## 12. Validation rules

Enforced by Pydantic V2 at the boundary and re-asserted in the service layer where the rule depends
on stored state. Each mirrors a Zod schema on the frontend (constitution Principle II, boundary
parity).

| Field | Rule | Source |
|---|---|---|
| `email` | RFC-shaped, ≤320 characters, lowercased on store, unique across all statuses, not matching `deleted_*@example.com` | FR-004, FR-022, FR-023 |
| `password` | ≥12 characters, ≤128, not in the bundled breached list | FR-014 |
| `first_name`, `last_name` | Non-empty after trimming, ≤100 characters | FR-005, FR-036 |
| `phone` | Parseable to E.164; stored normalized; optional except where a role requires it | FR-022, FR-036 |
| `business_name` | Required when role is `trainer`, ≤200 characters | FR-021 |
| `website` | Absolute `http`/`https` URL when present | FR-006 |
| `jersey_number` | ≤10 characters, alphanumeric | FR-006 |
| `photo` upload | Decodes as JPEG, PNG, or WebP; ≤5 MB; declared content type must match the decoded format | FR-034, R-07 |
| `reason` (erasure) | Non-empty after trimming, ≤1000 characters | FR-044 |
| `role` | One of the four enum values | FR-002, FR-030 |
| Directory `page_size` | 1–100, default 25 | FR-052 |
| Status transition | Must appear in §1's transition table | FR-003 |
| Profile write | Must not target `email`, `role`, `status`, `created_at`, or `skill_level` | FR-033 |
| Any nullable text field | The empty string is rejected (`min_length=1`); absence is spelled `null` at every layer; no nullable text column may hold `''`. An explicit `null` in a partial update clears the column; an omitted key leaves it unchanged | Constitution VI, FR-059 |
| `first_name`, `last_name` in a partial update | May be omitted, but an explicit `null` is rejected with a field-attributed 422 — both map to `NOT NULL` columns (§3) | FR-005, FR-036, Constitution VI |
| `phone` on account creation | Same rule as on profile save: parseable to E.164 and stored normalized. Enforced on **both** write paths, not only the profile one | FR-022, FR-036 |

---

## 13. Alembic revision plan

One revision per logical step, each independently reversible.

| # | Revision | Contents |
|---|---|---|
| 1 | `create_users_and_profiles` | `users`, `user_profiles`, enum check constraints, indexes |
| 2 | `create_role_detail_tables` | `trainer_organizations`, `coach_details`, `player_details`, `parent_contacts` |
| 3 | `create_auth_tables` | `sessions`, `credential_setup_invitations`, `sign_in_attempts` with composite indexes |
| 4 | `create_audit_and_erasure` | `audit_entries`, `erasure_records`, plus the append-only triggers on `audit_entries` |

Revision 4's triggers are raw DDL, which is unavoidable — a trigger is not expressible as an ORM or
Core construct. It is the second of the two documented deviations from the constitution's No Raw SQL
rule, both recorded in `plan.md` §Complexity Tracking.

---

## 14. Seed data

A single bootstrap Super Admin, created by an idempotent command reading email and password from the
environment, never from a committed default. Without it the platform has no way in, since every other
account requires a Super Admin to create it. The command refuses to run if any Super Admin already
exists, so it cannot be used to mint a second one, and it writes an `audit_entries` row attributed to
the bootstrap process.

---

# Extension: ShareLink Onboarding, Multi-Trainer & Portal Branding

**Date**: 2026-08-26 | **Inputs**: [spec.md](./spec.md) FR-065 – FR-104,
[research.md](./research.md) R-21 – R-33

Everything below is additive. No existing column changes type or nullability, and no existing row
is rewritten except by the backfill in revision 7, which only inserts.

## 15. New enumerations

### `ShareLinkKind`

| Value | Uses | Expiry | Addressed to | In scope here |
|---|---|---|---|---|
| `player_standing` | unlimited | none | anyone holding the link | **yes** |
| `coach_single_use` | 1 | 7 days | one named email | no — US-01.08 |

FR-072 requires the distinction to exist in the record now so the coach flow is additive later. Only
`player_standing` rows are ever written by this feature; the second value is a constraint the schema
already permits, not code that exists.

### `AssociationStatus`

| Value | Meaning |
|---|---|
| `active` | The player trains with this trainer. Appears in the switcher. |
| `inactive` | Retained for history; excluded from the switcher (FR-089). Nothing in this feature sets it — US-01.04 does. |

### `Gender` (R-32)

`male`, `female`, `other`, `prefer_not_to_say`. Persisted as constrained text, like `UserRole`.

## 16. `share_links`

A trainer's standing offer to join them (FR-065 – FR-069).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | text(36) | PK | UUIDv4. |
| `code` | text(64) | not null, **unique**, indexed | The URL-safe code, stored **as issued** — not hashed. R-21 argues why this token is the exception. `secrets.token_urlsafe(16)`, 22 characters, 128 bits. |
| `trainer_user_id` | text(36) | FK → `users.id`, not null, indexed | Owner (FR-067). |
| `created_by_user_id` | text(36) | FK → `users.id`, not null | The trainer, or the Super Admin whose account-creation transaction produced it. |
| `kind` | text | not null, check in `ShareLinkKind` | Always `player_standing` here. |
| `target_email` | text(320) | nullable | For `coach_single_use` only; always `NULL` in this feature. |
| `expires_at` | timestamptz | nullable | `NULL` means never (FR-065). |
| `max_uses` | integer | nullable | `NULL` means unlimited. |
| `use_count` | integer | not null, default 0 | Raised by exactly one per association produced (FR-068), never by a repeat visit (FR-082). |
| `is_active` | boolean | not null, default true | Cleared on regeneration (FR-069). |
| `revoked_at` | timestamptz | nullable | Set with `is_active = false`. |
| `created_at` | timestamptz | not null | |

**Indexes**: unique on `code` — the join path's only lookup, and it must be an index seek because it
is reachable unauthenticated; on `(trainer_user_id, is_active)` for "my current link".

A link admits a join only when `is_active`, `revoked_at IS NULL`, `expires_at` is null or future,
`max_uses` is null or above `use_count`, **and** the owning trainer's account is `active`. All five
are checked in one service predicate whose single refusal message satisfies FR-070's
non-disclosure clause — the caller cannot tell which condition failed.

Old rows are never deleted: `trainer_player_associations.share_link_id` references them, and FR-069
requires associations to outlive the link that made them.

## 17. `trainer_player_associations`

The many-to-many at the centre of the multi-trainer requirement (FR-084 – FR-092).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | text(36) | PK | |
| `trainer_user_id` | text(36) | FK → `users.id`, not null, indexed | |
| `player_user_id` | text(36) | FK → `users.id`, not null, indexed | |
| `share_link_id` | text(36) | FK → `share_links.id`, nullable | Which link produced it (FR-068). Nullable for associations a later epic creates by another route. |
| `status` | text | not null, check in `AssociationStatus`, default `active` | |
| `joined_at` | timestamptz | not null | |
| `updated_at` | timestamptz | not null | |

**Unique constraint** on `(trainer_user_id, player_user_id)` — this is what makes FR-082 true rather
than checked: a second join attempt hits the index, the service catches the integrity error and
returns "already connected" without raising `use_count`.

**Indexes**: the unique pair; `(player_user_id, status)` for the switcher; `(trainer_user_id,
status)` for the roster.

No cascade delete is relied on for erasure — erasure anonymizes rows rather than removing them
(§10), so an erased player keeps every association and appears on each roster as "Deleted User",
which is FR-091 and the reason SC-008's participant counts stay stable.

## 18. `link_lookup_attempts`

Durable counter behind FR-071 and SC-021, shaped like `sign_in_attempts` (R-30).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | integer | PK autoincrement | High volume, never referenced. |
| `client_ip` | text(45) | not null, indexed | The only dimension — an invalid code identifies no account. |
| `attempted_at` | timestamptz | not null, indexed | |
| `successful` | boolean | not null | Successful lookups recorded too, so the window clears. |

**Composite index** on `(client_ip, attempted_at)`. Ten unsuccessful rows in the trailing 15 minutes
refuse further lookups; the window slides, so access resumes on its own. Pruned by the existing
maintenance routine.

## 19. Columns added to existing tables

### 19.1 `player_details` — who the player is, and where they are looking

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `player_name` | text(200) | nullable | The player's name when it differs from the account holder's (FR-074). `NULL` means "the account holder is the player" and the name is read from `user_profiles`. |
| `date_of_birth` | date | nullable | R-31. Age is derived, never stored. |
| `gender` | text | nullable, check in `Gender` | |
| `is_self` | boolean | not null, default true | FR-077's answer: is the account holder the player, or responsible for one? Drives which age band applies at registration. |
| `active_trainer_user_id` | text(36) | FK → `users.id`, nullable, indexed | R-24. The active context. Nullable because zero associations is a valid state. |

`player_name` is nullable rather than duplicated from the profile so that correcting the account
holder's name does not leave a stale copy behind for a self-registered player.

`active_trainer_user_id` is **never trusted as read**. One service function resolves it, and when the
stored trainer is missing, its association is not `active`, or its account is not `active`, the
function selects another Active association, writes the correction back, and returns that — which is
FR-089 implemented once rather than at each caller.

### 19.2 `trainer_organizations` — the portal's identity

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `logo_key` | text(128) | nullable | Opaque storage key like `user_profiles.photo_key`, not a URL. `NULL` means the platform default (FR-104). |
| `primary_color` | text(7) | nullable | `#rrggbb`, stored exactly as chosen (R-29). `NULL` means the default. |
| `branding_updated_at` | timestamptz | nullable | |

Both value columns are nullable and mean "default" when absent — never `''` (constitution
Principle VI, FR-104).

## 20. Erasure, extended

Additions to §10's transformation table. The transaction gains these lines; nothing already in it
changes.

| Target | Before | After |
|---|---|---|
| `player_details.player_name` | `Sam Lee` | `NULL` — a name, and the erased account already reads as "Deleted User" |
| `player_details.date_of_birth` | a date | `NULL` — a date of birth is identifying |
| `player_details.gender` | a value | **unchanged** — a classification Epic-02 groups by, like `skill_level`; not an identifier on its own |
| `player_details.is_self`, `active_trainer_user_id` | either | **unchanged** / cleared to `NULL` respectively — an erased account has no context to be in |
| `trainer_player_associations.*` | any | **unchanged** (FR-091) — the roster keeps the row, showing "Deleted User" |
| `share_links` owned by an erased trainer | active | `is_active = false`, `revoked_at` set — the trainer is gone, the link must not admit anyone (FR-070) |
| `trainer_organizations.logo_key` | storage key | `NULL`, and the stored file removed — a logo identifies the business as directly as its name |
| `trainer_organizations.primary_color` | a hex value | **unchanged** — a colour identifies nobody |

The judgement recorded in §10 — that `business_name` survives — extends to `primary_color` for the
same reason and against the same caveat: for a sole trader, the brand is the person.

## 21. Relationships, extended

```
users (trainer) ──1───* share_links
     │                      │ 0..1
     │                      ▼
     └──1───* trainer_player_associations *───1── users (player_parent)
                                                        │ 1
                                                        ▼
                                              player_details
                                                 active_trainer_user_id ──▶ users (trainer)

users (trainer) ──1──1 trainer_organizations
                          logo_key, primary_color

link_lookup_attempts  — keyed by client_ip only, no FK to anything
```

`link_lookup_attempts` holds no foreign key for the same reason `sign_in_attempts` does not: the
attempts worth recording are the ones that match nothing.

## 22. Validation rules, extended

| Field | Rule | Source |
|---|---|---|
| ShareLink `code` | 22 URL-safe characters from 128 bits; unique; never displayed for a link that is not the trainer's own | FR-066, R-21 |
| `player_name` | 1–200 characters after trimming when present; `null` when the account holder is the player | FR-074, Constitution VI |
| `date_of_birth` | A real past date; derived age must be ≥18 when `is_self`, and 1–18 when not | FR-077, R-31 |
| `gender` | One of the four enum values | R-32 |
| Join by an existing association | Refused as "already connected"; `use_count` unchanged | FR-082 |
| Join by a non-`player_parent` role | Refused; nothing written | FR-081 |
| Registration email | Same rule as account creation, including the `deleted_*@example.com` refusal | FR-076, FR-004 |
| `PUT /me/trainer-context` body | The named trainer must have an `active` association with the caller; otherwise 404, not 403 — a trainer the caller is not associated with must not be confirmed to exist | FR-088, FR-090 |
| Logo upload | Decodes as PNG or JPEG **or** passes SVG screening (R-27); ≤2 MB; declared content type matches | FR-094, FR-095 |
| Logo dimensions | Raster logos above 200×200 are fitted to it preserving aspect ratio, never refused. Vector logos are not resized — they scale | FR-096 |
| `primary_color` | Matches `^#[0-9a-fA-F]{6}$`; stored lowercased | FR-098 |
| Any new nullable text field | Empty string rejected (`min_length=1`); absence is `null`; an explicit `null` clears, an omitted key does not | Constitution VI, FR-104 |

## 23. Alembic revisions 5–7

| # | Revision | Contents |
|---|---|---|
| 5 | `create_share_links_and_associations` | `share_links`, `trainer_player_associations`, `link_lookup_attempts`, with their check constraints and indexes |
| 6 | `extend_player_details_and_branding` | The five `player_details` columns and the three `trainer_organizations` columns, all nullable or defaulted so the migration needs no table rewrite |
| 7 | `backfill_trainer_share_links` | One `player_standing` link for every existing `trainer` account that has none |

Revision 7 is a **data** migration and is written with SQLAlchemy Core constructs against
`op.get_bind()` — a `select` for trainers without a link, an `insert` for the rows. No raw SQL, so it
adds no exception to the two in `plan.md` §Complexity Tracking. It is idempotent: re-running selects
nothing. Codes are generated in Python during the migration, so the entropy requirement holds for
backfilled links exactly as for new ones.

Revision 6 adds `is_self` with a server default of `true` so existing player rows are valid without a
rewrite; the default stays, because a registration always states it explicitly and a row created any
other way is a self-player by definition.

## 24. Seed data, extended

The bootstrap Super Admin command is unchanged. For local work and for the quickstart's US6 walk,
the seed path additionally creates one trainer whose standing link is printed to the console, since
a join link is otherwise only obtainable by signing in as a trainer and reading it — which is
exactly the loop the quickstart needs to break to test registration from a cold start.

---

# Extension: Parent/Child Family Accounts & the Approval Workflow

**Date**: 2026-08-27 | **Inputs**: [spec.md](./spec.md) FR-106 – FR-159,
[research.md](./research.md) R-34 – R-51

**This extension is not additive, and that is the headline.** Every previous slice could say "no
existing column changes type or nullability". This one cannot. `player_details.user_id` is a primary
key that also happens to be a foreign key to `users` — the schema's way of asserting *one player per
account* — and FR-106 removes exactly that assertion. So `player_details` is replaced by
`player_profiles` (R-34), `trainer_player_associations` is re-pointed at it (R-35), and the active
context moves to a table of its own (R-36). §35 lists every piece of existing code that assumes the
old shape, because that list is the real size of this slice.

## 25. New enumerations

All three are Python `enum.StrEnum` persisted as constrained text, joining `UserRole`,
`AccountStatus`, `ShareLinkKind`, `AssociationStatus`, and `Gender` in `models/enums.py`.

### `PlayerProfileKind`

| Value | Meaning |
|---|---|
| `self` | The account holder is this player. At most one per account (FR-106). Name and photo are read from `user_profiles` (R-37). Age must be 18 or above (FR-108). |
| `child` | A player the account holder is responsible for. Any number per account. Carries its own name and photo, because a child may have no `users` row at all. Age must be 1–18. |

### `ApprovalRequestKind`

| Value | Subject columns | Executed by this feature |
|---|---|---|
| `join_trainer` | `trainer_user_id`, optionally `share_link_id` | **yes** — the one kind whose subject exists today (R-46) |
| `usd_payment` | `amount_minor`, `currency` | no — rules and columns only; Epic-05 registers the executor |
| `token_spend` | `amount_minor`, `currency` | no — same |

FR-142 requires all three to exist in the record now. Only `join_trainer` rows are written by this
feature, and approving either other kind raises a domain error rather than recording an approval whose
action never happened (R-42, R-46).

### `ApprovalRequestStatus`

| Value | Live | Terminal | Set by |
|---|---|:---:|---|
| `pending_parent_approval` | yes | | Request creation; a child's reply to an information request |
| `info_requested` | yes | | The parent asking for more information |
| `approved` | | yes | The parent, with the action carried out in the same transaction |
| `denied` | | yes | The parent |
| `expired` | | yes | The maintenance sweep, 48 hours after the request was raised |
| `withdrawn` | | yes | The child who raised it |

Permitted transitions, enforced by the service and asserted by unit tests (FR-143):

```
pending_parent_approval ──┬─▶ info_requested
                          ├─▶ approved
                          ├─▶ denied
                          ├─▶ expired
                          └─▶ withdrawn

info_requested ───────────┬─▶ pending_parent_approval   (the child replies)
                          ├─▶ denied
                          ├─▶ expired
                          └─▶ withdrawn

approved / denied / expired / withdrawn ──▶ (nothing — terminal)
```

`info_requested` cannot go directly to `approved`: the parent asked a question, so the answer returns
the request to pending and they decide from there. Anything else is a domain error.

## 26. `player_profiles`

One player who trains (FR-106, FR-107). Replaces `player_details`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | text(36) | PK | UUIDv4. The identifier associations, contexts, and approval requests reference. |
| `account_user_id` | text(36) | FK → `users.id`, cascade delete, not null, indexed | The account that owns this profile. Always a `player_parent` account (FR-109). |
| `kind` | text | not null, check in `PlayerProfileKind` | |
| `first_name` | text(100) | **nullable** | `NULL` exactly when `kind = 'self'`; read from `user_profiles` then (R-37). |
| `last_name` | text(100) | **nullable** | Same rule. |
| `photo_key` | text(128) | nullable | Opaque storage key behind the existing photo port. For a `self` profile this stays `NULL` and `user_profiles.photo_key` is used. |
| `date_of_birth` | date | nullable | Age is derived, never stored (R-31, carried over). Nullable **only** so revision 9 can migrate rows that never had one; required by the schema on every new write. |
| `gender` | text | nullable, check in `Gender` | |
| `school` | text(200) | nullable | Self-editable (FR-107). |
| `jersey_number` | text(10) | nullable | Text, not integer — unchanged reasoning from §4.3. |
| `skill_level` | text(50) | nullable | Never writable by the family (FR-107, FR-007). |
| `tokens_without_approval` | boolean | not null, default `false` | The one per-child permission (FR-146, R-44). The default is in the schema because it is a safety property. |
| `sign_in_user_id` | text(36) | FK → `users.id`, nullable, **unique** | The child's own account when the parent granted one (FR-129). `NULL` means no separate sign-in. |
| `removed_at` | timestamptz | nullable | Soft removal (FR-111). `NULL` means the profile is live. |
| `created_at` | timestamptz | not null | |
| `updated_at` | timestamptz | not null | |

**Check constraints:**

| Name | Rule | Why |
|---|---|---|
| `ck_player_profiles_kind` | `kind` in `PlayerProfileKind` | Closed set. |
| `ck_player_profiles_gender` | `gender` null or in `Gender` | Matches the existing `ck_player_details_gender`. |
| `ck_player_profiles_self_names` | `(kind = 'self' AND first_name IS NULL AND last_name IS NULL) OR (kind = 'child' AND first_name IS NOT NULL AND last_name IS NOT NULL)` | Makes R-37's two cases exhaustive and mutually exclusive, so no row is ambiguous about which name is authoritative. |
| `ck_player_profiles_signin_is_child` | `sign_in_user_id IS NULL OR kind = 'child'` | A `self` profile's sign-in *is* the account; a second credential for it would be a duplicate account for one person. |

**Indexes:**

- `uq_player_profiles_one_self` — **partial** unique index on `(account_user_id)`
  `WHERE kind = 'self'`. This is what makes FR-106's "at most one of the account holder's own kind"
  true by construction rather than checked, and Story 9 scenario 8 a 409 rather than a race.
- Unique on `sign_in_user_id` — one credential belongs to one child.
- `(account_user_id, removed_at)` — the family list, which reads live profiles for one account.
- `(sign_in_user_id)` covered by the unique index — the lookup R-38 folds into current-user
  resolution.

**Why `removed_at` rather than a status enum**: a profile has exactly two states, and FR-111 asks only
that removal preserve history. A nullable timestamp says when it happened as well as whether, which a
boolean would not, and it avoids a third enum that would then need its own transition table.

### 26.1 The one duplication this design accepts, and how it is contained

A child granted a sign-in gets a `users` row, and §3 requires **every** account to hold a
`user_profiles` row with non-null `first_name` and `last_name`. So a child with a sign-in has their
name in two places: `player_profiles` (where R-37 puts it, and where it must be, because a child
*without* a sign-in has no other home) and `user_profiles` (where the account table requires it).

This is stated rather than discovered because it is the one place this slice tolerates a copy, and an
implementer who meets it mid-task will otherwise invent a third answer.

- **The profile is authoritative.** `player_profiles.first_name`/`last_name` is the source of truth for
  a child's name, in every read, for every viewer.
- **There is exactly one writer.** The service that edits a child profile writes both rows in one
  transaction; granting a sign-in seeds `user_profiles` from the profile. No other code path writes a
  child account's `user_profiles` names.
- **Nothing reads the copy.** Rosters, switchers, approval queues, and the child's own views all read
  the profile. The `user_profiles` row exists to satisfy the account invariant, not to be displayed.

**Alternatives weighed and rejected**: relaxing `user_profiles.first_name` to nullable — it would
weaken an invariant every one of the four roles currently relies on, to accommodate one case. Moving a
child-with-sign-in's name onto `user_profiles` and leaving the profile's columns null — then granting
a sign-in *moves* the name and revoking it loses the name, which is absurd. Deriving `user_profiles`
names with a database trigger — a third raw-SQL exception for a copy one service method already
maintains.

**Photos take the simpler path**: `player_profiles.photo_key` is authoritative and
`user_profiles.photo_key` stays `NULL` for a child account, because §3 permits it to be null. Only
the names are duplicated, because only the names are `NOT NULL`.

## 27. `active_training_contexts`

Which player profile and which trainer a signed-in account is currently looking at (FR-117, FR-120,
R-36). Replaces `player_details.active_trainer_user_id`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `user_id` | text(36) | PK, FK → `users.id`, cascade delete | One context per signed-in account — a parent and each child with a sign-in hold their own. |
| `player_profile_id` | text(36) | FK → `player_profiles.id`, nullable | Nullable because holding no live association is a valid state. |
| `trainer_user_id` | text(36) | FK → `users.id`, nullable | Same. |
| `updated_at` | timestamptz | not null | |

The stored pair is **never trusted as read**, exactly as `active_trainer_user_id` was not (R-24). One
service function validates that the profile is still live and still reachable by this caller, that the
association is still `active`, and that the trainer's account is still `active`; on any failure it
selects another available pair, writes the correction back, and returns that. Both columns are
nullable together — a row with one set and the other null is not a state the service ever writes, and
the resolver treats it as no context at all.

**Why a row per account rather than a nullable pair on `users`**: three of the four roles can never
hold a training context, and `users` is the most-read table in the system (R-36).

## 28. `approval_requests`

The Pending Parent Approval workflow (FR-141 – FR-159). One table, typed subject columns, no JSON
payload (R-39).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | text(36) | PK | |
| `player_profile_id` | text(36) | FK → `player_profiles.id`, not null, indexed | The child the request concerns. |
| `parent_user_id` | text(36) | FK → `users.id`, not null, indexed | The account that must resolve it. Recorded here rather than reached through the profile, so the responsible adult at the time of the request is fixed. |
| `kind` | text | not null, check in `ApprovalRequestKind` | |
| `status` | text | not null, check in `ApprovalRequestStatus`, indexed | |
| `trainer_user_id` | text(36) | FK → `users.id`, nullable | Subject of a `join_trainer` request. |
| `share_link_id` | text(36) | FK → `share_links.id`, nullable | Which link the child followed, when there was one. |
| `amount_minor` | integer | nullable | Minor currency units — an integer, never a float (R-39). The amount **as shown to the parent** (FR-152). |
| `currency` | text(3) | nullable | ISO 4217. |
| `requested_at` | timestamptz | not null | |
| `expires_at` | timestamptz | not null, indexed | `requested_at + 48 hours`, written once and never recomputed (R-43, FR-155). |
| `parent_note` | text(1000) | nullable | Attached to an approval, a denial, or an information request (FR-150). |
| `child_note` | text(1000) | nullable | The child's reply to an information request. |
| `resolved_at` | timestamptz | nullable | |
| `resolved_by_user_id` | text(36) | FK → `users.id`, nullable | The parent, the child (for a withdrawal), or `NULL` for an expiry, which no one performed. |

**Check constraints:**

| Name | Rule | Why |
|---|---|---|
| `ck_approval_requests_kind` / `_status` | Closed sets | |
| `ck_approval_requests_subject` | `(kind = 'join_trainer' AND trainer_user_id IS NOT NULL AND amount_minor IS NULL AND currency IS NULL) OR (kind IN ('usd_payment','token_spend') AND amount_minor IS NOT NULL AND currency IS NOT NULL AND trainer_user_id IS NULL)` | The subject matches the kind, at the schema level. This is what a JSON payload could not give (R-39). |
| `ck_approval_requests_resolution` | Live statuses require `resolved_at IS NULL`; terminal statuses require `resolved_at IS NOT NULL` | A resolved request always says when. |
| `ck_approval_requests_expiry_actor` | `status <> 'expired' OR resolved_by_user_id IS NULL` | Expiry is the one resolution with no actor, and recording a spurious one would misattribute a decision nobody took. |

**Indexes:**

- `uq_approval_requests_live` — **partial** unique index on
  `(player_profile_id, kind, trainer_user_id)` `WHERE status IN ('pending_parent_approval',
  'info_requested')`. FR-139's "no second request while one is pending" by construction (R-40). It is
  partial so that a denied request does not bar the child from ever asking again.
- `(parent_user_id, status)` — the parent's pending list (FR-149).
- `(player_profile_id, status)` — the child's own view of what they asked for (FR-153).
- `(status, expires_at)` — the sweep's only query (R-43); it must be an index scan, not a table scan.

**One honest limitation of the partial index**: SQLite treats `NULL`s as distinct in a unique index,
and the two financial kinds carry `trainer_user_id IS NULL`. So the index bites for `join_trainer` —
the only kind this feature creates — and does not constrain duplicate pending payment requests. That
is correct today, because a payment's real subject is an event that does not exist until Epic-02;
when it does, the subject column joins this index and the guarantee extends with it. Recorded rather
than discovered.

## 29. Changes to existing tables

### 29.1 `trainer_player_associations` — the association's subject moves

| Change | Detail |
|---|---|
| **Added** | `player_profile_id` text(36), FK → `player_profiles.id`, not null (after revision 10), indexed |
| **Dropped** | `player_user_id` — the account-level reference (R-35) |
| **Unique constraint** | `uq_trainer_player` moves from `(trainer_user_id, player_user_id)` to `(trainer_user_id, player_profile_id)` |
| **Index** | `ix_tpa_player_status` moves from `(player_user_id, status)` to `(player_profile_id, status)` |
| **Unchanged** | `id`, `trainer_user_id`, `share_link_id`, `status`, `joined_at`, `updated_at`, and `ix_tpa_trainer_status` |

The unique constraint is load-bearing and must stay load-bearing: it is what makes FR-082's
"already connected" a caught integrity error rather than a checked precondition, and the same is now
true at profile granularity for FR-126's re-add case (Story 10 scenario 4). `AssociationStatus`
gains its first writer in this slice — §15 noted that nothing set `inactive` and that US-01.04 would;
FR-126 is that requirement.

### 29.2 `player_details` — dropped

Every column migrates to `player_profiles`: `school`, `jersey_number`, `skill_level`,
`date_of_birth`, `gender` directly; `player_name` into `first_name`/`last_name` under R-37's rule;
`is_self` into `kind`; `active_trainer_user_id` into `active_training_contexts`. The table is then
dropped rather than left as an empty shell (R-34).

### 29.3 `parent_contacts` — unchanged, and now load-bearing

Not one column changes. What changes is its standing: FR-113 makes it the family's single contact
record, held against the account and serving every child on it, which is what §4.4 already described
as "one family account that may both train and parent". A child profile carries no contact detail of
its own, deliberately — that is the epic's "shares parent's contact info".

### 29.4 `users` — unchanged

No column is added. A child's account is an ordinary `player_parent` row (R-38), and "this is a child
account" is derived from the existence of a `player_profiles` row whose `sign_in_user_id` names it.
No `account_kind` column exists, so the two facts cannot diverge.

## 30. Erasure, extended again

Additions to §10 and §20. The transaction gains these lines.

| Target | Before | After |
|---|---|---|
| `player_profiles.first_name` / `last_name` (child) | `Alex Lee` | `Deleted` / `User` — not `NULL`, because `ck_player_profiles_self_names` requires a child to have a name, and the roster must still read "Deleted User" (FR-091) |
| `player_profiles.first_name` / `last_name` (self) | already `NULL` | **unchanged** — the account's own profile is anonymized by §10 |
| `player_profiles.photo_key` | storage key | `NULL`, and both stored image files removed |
| `player_profiles.date_of_birth` | a date | `NULL` — identifying, as §20 already established |
| `player_profiles.school`, `jersey_number` | free text | `NULL` |
| `player_profiles.gender`, `skill_level` | a value | **unchanged** — classifications later epics group by, not identifiers (§20's reasoning) |
| `player_profiles.tokens_without_approval` | either | `false` — no permission survives the person |
| `player_profiles.sign_in_user_id` | an account id | `NULL`, **and that child account is itself erased** — see below |
| `player_profiles.removed_at` | either | **unchanged** |
| `active_training_contexts` rows for the account and each child sign-in | possibly set | deleted — an erased account has no context to be in |
| `approval_requests` in a live status | pending | `expired`, `resolved_at` set, `resolved_by_user_id` `NULL` — no one can approve for an erased family (FR-157) |
| `approval_requests.parent_note`, `child_note` | free text | `NULL` — free text written by a person may name them, exactly as §10 treats a coach's biography |
| `approval_requests` otherwise | any | **unchanged** — kind, amount, timestamps, and outcome survive, so FR-047's totals do |
| `trainer_player_associations.*` | any | **unchanged** (FR-091) — every roster keeps its row |

**Erasing a parent cascades to their children's sign-ins.** A child account is personal data about a
child, so erasing the family must erase it too: each `sign_in_user_id` account goes through the same
anonymization as the parent, in the same transaction. This is stated here because it is the one place
erasure reaches an account other than the one named, and because getting it wrong would leave a
signed-in child able to act on behalf of an erased family. Participant counts are unaffected — the
child profile survives as "Deleted User" on every roster, which is the row the counts read.

**One judgement recorded, in the same spirit as §10's two**: a child's `date_of_birth` is cleared but
`gender` is not, matching §20's treatment of the account holder. For a family of one child this makes
the surviving classification weakly identifying in combination with the trainer's roster. The
alternative — clearing it — costs Epic-02 its age-and-gender grouping for historical events, which
FR-047 protects. The same caveat and the same one-line fallback as §10 apply.

## 31. Relationships, extended

```
users (parent, player_parent) ──1───* player_profiles
     │                                     │ 0..1  sign_in_user_id
     │ 1                                   ▼
     └──1 parent_contacts            users (child, player_parent)
                                            │ 1
                                            ▼
                                     active_training_contexts  (one per signed-in account)
                                            │ 0..1        │ 0..1
                                            ▼             ▼
                                     player_profiles   users (trainer)

player_profiles ──1───* trainer_player_associations *───1── users (trainer)
                │                       │ 0..1
                │                       ▼
                │                  share_links
                │
                └──1───* approval_requests ───1── users (parent, resolver)
                                  │ 0..1
                                  ▼
                            users (trainer)  +  share_links
```

Two shapes worth reading twice. First, `player_profiles` points at `users` **twice** — once for the
owning account and once, optionally, for the child's own credential — and those are different
accounts. Second, `active_training_contexts` is keyed by the *viewer*, not the profile, which is why a
parent and their signed-in child can look at the same profile through different contexts without
either overwriting the other (R-36).

## 32. Validation rules, extended

| Field | Rule | Source |
|---|---|---|
| `kind` | One of two enum values; at most one `self` per account, enforced by a partial unique index | FR-106 |
| `first_name`, `last_name` (child) | 1–100 characters after trimming, required | FR-107, FR-112 |
| `first_name`, `last_name` (self) | Must be absent; supplying them is a 422, not a silent no-op | R-37 |
| `date_of_birth` | A real past date; derived age ≥18 when `kind = 'self'`, 1–18 when `kind = 'child'`. Required on every new write | FR-108 |
| `gender` | One of the four enum values, required on creation | FR-107 |
| Duplicate child | Same account, same `date_of_birth`, case-insensitive match on trimmed first **and** last name → 409 unless `acknowledge_possible_duplicate` is true | FR-110, R-45 |
| Child sign-in email | Same rule as account creation — unique across all statuses, not matching `deleted_*@example.com`; refused if it is the parent's own address | FR-129, FR-004 |
| Profile ownership | Every `/me/players/{profile_id}` route refuses a profile whose `account_user_id` is not the caller — 404, not 403, so a profile on another account is not confirmed to exist | FR-112 |
| Child's reachable profile | A signed-in child may name only the profile their `sign_in_user_id` is attached to; a sibling's id is a 404 | FR-132, R-48 |
| Association removal | Addressed by `association_id`, which must belong to a profile the caller owns | FR-126, R-48 |
| Add trainer by selection | The named trainer must hold an `active` association with **some** profile on the caller's account; otherwise 404 | FR-125 |
| `PUT /me/context` body | The pair must be a live profile the caller may reach with an `active` association to that trainer; otherwise 404 | FR-117, FR-119 |
| `tokens_without_approval` | Boolean, writable only by the owning parent — a child's attempt is refused | FR-132, FR-147 |
| Approval resolution | Only `parent_user_id` (or a Super Admin); only from a live status; only before `expires_at`; only while the parent is Active | FR-156, FR-157 |
| Withdrawal | Only by the child the request concerns, only from a live status | FR-154 |
| `parent_note`, `child_note` | 1–1000 characters after trimming when present; `null` when absent, never `''` | Constitution VI |
| `amount_minor` | Positive integer; `currency` a three-letter code — both required for a financial kind and forbidden otherwise | R-39 |
| Approving a financial kind | Refused with a domain error while no executor is registered | FR-142, R-46 |
| Any new nullable text field | Empty string rejected (`min_length=1`); absence is `null`; an explicit `null` clears, an omitted key does not | Constitution VI, FR-059 |

## 33. Alembic revisions 8–10

Three revisions, splitting structure from data from constraints (R-35). HEAD moves `0007` → `0010`.

| # | Revision | Contents |
|---|---|---|
| 8 | `create_player_profiles_and_approvals` | Creates `player_profiles` (with its four check constraints and the partial one-self index), `active_training_contexts`, and `approval_requests` (with its four check constraints and the partial live index). Adds `trainer_player_associations.player_profile_id` as **nullable**, with its foreign key and index. Nothing is dropped and nothing is required, so the application keeps working unchanged on this revision. |
| 9 | `migrate_players_to_profiles` | **Data migration**, SQLAlchemy Core against `op.get_bind()`. One `player_profiles` row per `player_details` row: `kind` from `is_self`, names split from `player_name` for a child and left `NULL` for a self player, every other column copied. Then `player_profile_id` backfilled on every association by joining `player_user_id` to the new row's `account_user_id`. Then one `active_training_contexts` row per player whose `active_trainer_user_id` was set, resolving the profile as that account's single profile. Idempotent: re-running selects nothing. |
| 10 | `finalize_profile_associations` | Under `batch_alter_table`: makes `player_profile_id` non-nullable, drops `uq_trainer_player` and recreates it on `(trainer_user_id, player_profile_id)`, drops `ix_tpa_player_status` and recreates it on `(player_profile_id, status)`, drops `player_user_id`. Then drops `player_details`. |

Revision 9 uses Core `select`/`insert`/`update` exactly as revision 7's backfill did, so **the two
documented raw-SQL exceptions in `plan.md` §Complexity Tracking stay at two**. The CI grep that
forbids `.execute("` outside `db/engine.py` continues to pass.

**Splitting a `player_name` into two columns**: revision 9 splits on the last space — everything
before it is the first name, everything after is the last. Where there is no space, the whole value
becomes the first name and the last name becomes `'—'`, because
`ck_player_profiles_self_names` requires a child to have both and refusing the migration over a
one-word name would block the upgrade. The heuristic is recorded here rather than left in the
migration for someone to discover, and it applies only to rows created before this slice; every new
child supplies both names as separate fields.

**Downgrade behaviour, and its deliberate limit**: revisions 8 and 10 reverse cleanly. Revision 9's
`downgrade()` restores `player_details` rows from `player_profiles` **only when every account holds
exactly one profile**, and otherwise **raises**, because a parent's three children cannot be
represented in a table keyed by account. A migration that silently discarded two of them would be
worse than one that refuses to run, so the refusal is the designed behaviour and is asserted by a
test.

**Verification point**: revision 9 is the one to check before proceeding. `test_migration_backfill.py`
gains assertions that the association count is unchanged across 8→9→10, that every association has a
`player_profile_id`, and that every account with a former context has exactly one
`active_training_contexts` row.

## 34. Seed data, extended

`bootstrap-superadmin` and `seed-demo-trainer` are unchanged. `seed-demo-trainer` gains one line of
output: alongside the trainer's join link it prints nothing new, but a third command,
`seed-demo-family`, creates a parent with a `self` profile, two children — one with a sign-in and one
without — and one pending `join_trainer` request, printing the parent's and the child's credentials.
The quickstart's US9–US12 walks need a family that already has a pending request, and building one by
hand means signing in as a child, following a link, and signing back in as the parent before any
assertion can be made.

`prune` gains approval expiry (R-43), so its help text names both effects rather than only pruning.

## 35. What the migration touches — the blast radius

Recorded because §29's four table changes understate the work. Everything below assumes one player per
account today.

**Backend, must change:**

| Location | Assumption to remove |
|---|---|
| `repositories/user_repository.py` — `get_role_detail` | Returns `tuple[PlayerDetail, ParentContact \| None]` for a `player_parent`. The tuple's first element becomes a *list* of profiles, or the profile leaves this method entirely. |
| `repositories/user_repository.py` — `insert_join_registration` | Writes one `PlayerDetail` keyed by the new account; must write a `player_profiles` row instead. |
| `repositories/association_repository.py` — `list_active_for_player`, `list_for_trainer`, `count_for_trainer`, `get`, `insert`, `TrainerRosterRow` | All five join on the account id; all must join on the profile id, and the roster row gains the profile identity plus the responsible parent's contact. |
| `services/trainer_context_service.py` — all three methods | Reads and writes `player_details.active_trainer_user_id`; becomes the pair resolver over `active_training_contexts` (R-36). Renamed to match, since it no longer resolves only a trainer. |
| `services/join_service.py` — `register`, `accept`, `_viewer_state` | Writes `active_trainer_user_id` in two places; `accept` gains the family-member selection of FR-122 and Story 13, and `_viewer_state` gains the blocked-child branch of FR-137. |
| `services/erasure_service.py` — `_anonymize_role_detail` | Clears three `player_details` columns; becomes §30's larger transformation, including the cascade to child sign-ins. |
| `services/profile_service.py` — `_apply_role_detail_updates`, `editable_fields_for` | The player fields it edits move off the account's role detail. |
| `schemas/role_detail.py` — `build_role_detail_out` | Builds `PlayerParentDetail` from the tuple; that schema loses the player fields (R-34, R-49). |
| `api/v1/auth_router.py` — `_to_current_user` | Fills `active_trainer_id` and `trainer_count`; becomes the profile-aware pair plus a count of pairs. |
| `core/deps.py` — `get_trainer_context`, `TrainerContextDep` | Becomes `get_training_context` returning a validated pair (R-48). |

**Frontend, must change in lockstep:**

`shared/api/types.ts` (`TrainerContextEntry`, `TrainerPlayerSummary`, `CurrentUser.active_trainer_id`
and `trainer_count`, `JoinResult`, `PlayerParentDetail`); `entities/trainer-context/api/query-keys.ts`
(`ctxKeys` gains the profile dimension, R-47); `entities/trainer-context/api/use-trainers.ts` and
`use-switch-context.ts`; `widgets/trainer-context-switcher` (keyed on trainer today, must group by
profile per FR-118 and FR-119).

**Tests that encode the old shape:**

`tests/helpers.py` — `create_player_with_detail` creates one `PlayerDetail` per account and is used
throughout; it becomes a profile factory, and a family factory joins it. Existing suites to update:
`test_trainer_context.py`, `test_context_repair.py`, `test_trainer_roster.py`,
`test_trainer_isolation.py`, the `test_join_*.py` set, `test_erasure_associations.py`,
`test_migration_backfill.py`, `test_permission_matrix.py`, `contract/test_openapi_contract.py`, and on
the frontend `trainer-context-switcher.test.tsx`, `ctx-namespace.test.ts`, `join.test.tsx`.

This list is the argument for carrying all three migrations and the whole repository rework in one
foundational phase rather than spreading them across the user stories — see `plan.md`
§Implementation Sequence for the extension.
