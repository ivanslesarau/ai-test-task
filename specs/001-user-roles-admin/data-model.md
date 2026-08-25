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
