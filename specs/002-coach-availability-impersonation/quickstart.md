# Quickstart & Validation Guide

**Feature**: `002-coach-availability-impersonation` | **Date**: 2026-08-28

**What this is**: the runnable walk-through that proves the three slices of this feature work end to
end, story by story, plus the quality gates a change must pass before it is mergeable. It assumes the
environment feature 001 already documents; only what this feature *adds* is repeated here.

**What this is not**: implementation. No model, service, router, component, or migration body appears
here — those belong to `tasks.md` and the implementation phase.

---

## 1. Prerequisites

Feature `001-user-roles-admin` running, per its own
[quickstart](../001-user-roles-admin/quickstart.md) §1 – §3: backend on `:8000`, frontend on `:5173`,
a bootstrapped Super Admin, and `EMAIL_BACKEND=filesystem` so invitations land in
`backend/var/outbox/` as readable files.

Two settings are **new** in this feature and must be added to `.env` (the app refuses to start
without them — no production-wrong defaults, per the constitution):

| Variable | Example | Notes |
|---|---|---|
| `COACH_INVITATION_TTL_DAYS` | `7` | FR-002. The seven-day single-use window |
| `IMPERSONATION_MAX_MINUTES` | `60` | FR-046. The one-hour ceiling, measured from the start |

Then apply the one new migration:

```bash
cd backend
uv run alembic upgrade head        # revision 0011 — see data-model.md §110
uv run alembic current             # expect: 0011 (head)
```

Verify the schema landed and — critically — that the audit table's append-only triggers **survived**
the column addition (research.md R2-17 explains why this is the check that matters):

```bash
uv run python - <<'PY'
import sqlite3
db = sqlite3.connect("var/app.db")
tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert {"coach_invitations", "availability_slots", "impersonation_sessions"} <= tables, tables
triggers = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
assert {"trg_audit_entries_no_update", "trg_audit_entries_no_delete"} <= triggers, triggers
assert {"trg_impersonation_sessions_no_delete",
        "trg_impersonation_sessions_no_update_closed"} <= triggers, triggers
print("schema OK:", len(tables), "tables,", len(triggers), "triggers")
PY
```

Fixture accounts used below — create them through the API as feature 001's quickstart describes:

| Handle | Role | Notes |
|---|---|---|
| `admin@example.org` | Super Admin | The bootstrapped account |
| `trainer-a@example.org` | Trainer | Active, with branding set |
| `trainer-b@example.org` | Trainer | A second trainer, for the one-trainer-per-coach checks |
| `parent@example.org` | Player/Parent | Own profile plus two child profiles (Grace, Leo) |
| `grace@example.org` | Child sign-in | Granted by the parent, per feature 001 |

`$C` below is a cookie jar: `curl -c cookies.txt -b cookies.txt`. Sign in first:

```bash
curl -s -c cookies.txt -X POST localhost:8000/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"trainer-a@example.org","password":"..."}' | jq .role
```

---

## 2. US1 + US2 — A trainer invites a coach; the coach joins one trainer

### 2.1 Issue an invitation (FR-001 – FR-003, FR-008)

```bash
curl -s -b cookies.txt -X POST localhost:8000/api/v1/trainer/coach-invitations \
  -H 'content-type: application/json' \
  -d '{"email":"sam@example.org","invitee_name":"Sam","message":"Spring program"}' | jq
```

**Expect**: `201`; `state: "awaiting"`; `expires_at` seven days out; `invitee_name` and `message`
echoed. A file appears in `backend/var/outbox/` containing the trainer's business name, the message,
and a URL of the form `http://localhost:5173/coach-invite/<token>`.

**Expect also**: the response is byte-identical in shape whether or not `sam@example.org` already
holds an account — FR-008. Try it with the parent's address on a second trainer to confirm nothing in
the body or status differs.

Save the token: `TOKEN=$(ls -t backend/var/outbox/*.txt | head -1 | xargs grep -o 'coach-invite/[A-Za-z0-9_-]*' | cut -d/ -f2)`

### 2.2 Track it (FR-004)

```bash
curl -s -b cookies.txt localhost:8000/api/v1/trainer/coach-invitations | jq '.items[0] | {state, invited_email, expires_at}'
```

**Expect**: exactly one row, `awaiting`.

### 2.3 The duplicate guard (FR-007)

Re-issue to the same address. **Expect**: `409`, code `coach_invitation_pending`, and
`error.invitation` naming the existing row — not a second invitation.

### 2.4 Resend supersedes (FR-005)

```bash
OLD=$TOKEN
curl -s -b cookies.txt -X POST localhost:8000/api/v1/trainer/coach-invitations/<id>/resend | jq .expires_at
curl -s localhost:8000/api/v1/coach-invitations/$OLD | jq .error.code
curl -s -b cookies.txt localhost:8000/api/v1/trainer/coach-invitations | jq '.items | length'
```

**Expect**: `201` with a later `expires_at`; the **old** token now `404 invitation_link_invalid`; the
trainer's list still shows **one** invitation for that address, not two (superseded rows are never
listed).

### 2.5 Revoke (FR-006)

Issue a fresh invitation to `dana@example.org`, revoke it, then follow the link.
**Expect**: `422` if you try to revoke an already-accepted or already-revoked one; the link `404`s
after a successful revoke; the trainer's list shows `revoked`.

### 2.6 A brand-new coach registers (FR-011, FR-013, FR-017)

```bash
curl -s localhost:8000/api/v1/coach-invitations/$TOKEN | jq '{invited_email, account_exists, trainer}'
curl -s -c coach.txt -X POST localhost:8000/api/v1/coach-invitations/$TOKEN/register \
  -H 'content-type: application/json' \
  -d '{"first_name":"Sam","last_name":"Reyes","password":"correct-horse-battery","bio":"Guard skills"}' | jq
```

**Expect**: the preview shows the invited address in full, `account_exists: false`, and the trainer's
business name and branding. The register call returns `201`, `outcome: "joined"`, sets a session
cookie, and — crucially — **took no `email`, `role`, or `trainer_id`**: all three came from the
invitation.

Then:

```bash
curl -s -b coach.txt localhost:8000/api/v1/auth/session | jq '{role, portal_branding}'
curl -s -b cookies.txt localhost:8000/api/v1/trainer/coaches | jq '.items[0] | {first_name, joined_at}'
```

**Expect**: `role: "coach"`; `portal_branding` is **trainer A's**, not the platform default
(research.md R2-06 — this closes an existing TODO); and the coach appears on trainer A's roster with a
`joined_at`.

### 2.7 The one-trainer rule (FR-015, FR-019, SC-003)

As trainer B, invite `sam@example.org`. As Sam (signed in), accept it:

```bash
curl -s -b coach.txt -X POST localhost:8000/api/v1/coach-invitations/$TOKEN_B/accept | jq
```

**Expect**: `409`, code `coach_already_assigned`. **Then grep the entire response for trainer A's
name, business name, and id — it must appear nowhere** (SC-003). Trainer B's list now shows the
invitation as `blocked`; trainer B sees no hint of who Sam works for. The invitation is *not* spent:
`GET /coach-invitations/$TOKEN_B` still returns `200`.

### 2.8 Wrong role, wrong address, and the no-op (FR-013, FR-014, FR-016)

| Attempt | Expect |
|---|---|
| The parent account accepts a coach invitation | `403 role_cannot_accept`; the parent's role is unchanged |
| Sam accepts a *trainer A* invitation issued to a different address | `403 coach_invitation_address_mismatch`, naming the invited address |
| Sam accepts a second trainer A invitation while already on that roster | `200`, `outcome: "already_on_this_roster"`; roster count unchanged |

### 2.9 Ending an assignment frees the coach (FR-021, FR-022)

```bash
curl -s -b cookies.txt -X DELETE localhost:8000/api/v1/trainer/coaches/<coach_user_id> -o /dev/null -w '%{http_code}\n'
curl -s -b coach.txt localhost:8000/api/v1/auth/session | jq .portal_branding.logo_url
```

**Expect**: `204`; the coach's branding falls back to the platform default; the coach's own profile
and stated times are untouched; and trainer B's invitation can now be accepted successfully.

### 2.10 Audit trail (FR-023)

```bash
curl -s -b admin.txt "localhost:8000/api/v1/admin/users/<coach_user_id>/audit" | jq '.items[].action'
```

**Expect**: `coach_invitation_accepted` and `coach_assignment_ended` among the actions.

---

## 3. US3 + US4 — Stating a week ("My Times" and family Availability)

### 3.1 A coach states their week (FR-024, FR-026, FR-029)

```bash
curl -s -b coach.txt localhost:8000/api/v1/me/availability | jq
curl -s -b coach.txt -X PUT localhost:8000/api/v1/me/availability \
  -H 'content-type: application/json' -d '{"slots":[
    {"day_of_week":0,"start_minute":960,"end_minute":1080},
    {"day_of_week":0,"start_minute":1140,"end_minute":1260},
    {"day_of_week":5,"start_minute":540,"end_minute":720}]}' | jq
```

**Expect**: the first call returns `{"slots":[],"updated_at":null}` — "no times set", not
"unavailable" (FR-035). The save returns the week ordered by `(day_of_week, start_minute)` with a
fresh `updated_at`. Monday holds **two** non-overlapping ranges (16:00–18:00 and 19:00–21:00).

Sign out and back in; read again. **Expect**: byte-identical slots (SC-007).

### 3.2 Every refusal names the day, and changes nothing (FR-027, FR-028, SC-008)

Run each of these and confirm the stored week is unchanged after every one:

| Submitted | Expect |
|---|---|
| Two overlapping ranges on Monday | `422`, `fields[0].field` names Monday, message says overlap |
| `start_minute >= end_minute` | `422`, names the day |
| `end_minute: 1500` (past midnight) | `422`, names the day |
| Seven ranges on one day | `422`, names the day and the six-range limit |
| `start_minute: 967` (off the grid) | `422` |
| Two ranges that **touch** (…1080 then 1080…) | `200` — valid, explicitly (FR-027) |

```bash
# after each refusal:
curl -s -b coach.txt localhost:8000/api/v1/me/availability | jq '.slots | length'   # unchanged
```

### 3.3 Clearing is not the same as never having stated (FR-030, FR-032)

```bash
curl -s -b coach.txt -X DELETE localhost:8000/api/v1/me/availability -o /dev/null -w '%{http_code}\n'
curl -s -b coach.txt localhost:8000/api/v1/me/availability | jq
```

**Expect**: `204`, then `{"slots":[],"updated_at":"<just now>"}` — empty slots with a **non-null**
timestamp. The frontend renders both cases as "No times set", the second with its revision date.

### 3.4 A parent states a separate week per profile (FR-025, FR-033, SC-006)

```bash
curl -s -b parent.txt localhost:8000/api/v1/me/players | jq '.items[] | {id, first_name, kind}'
curl -s -b parent.txt -X PUT localhost:8000/api/v1/me/players/$GRACE/availability \
  -H 'content-type: application/json' \
  -d '{"slots":[{"day_of_week":1,"start_minute":1020,"end_minute":1200}]}' | jq .slots
curl -s -b parent.txt -X PUT localhost:8000/api/v1/me/players/$LEO/availability \
  -H 'content-type: application/json' \
  -d '{"slots":[{"day_of_week":5,"start_minute":540,"end_minute":720}]}' | jq .slots
curl -s -b parent.txt localhost:8000/api/v1/me/players/$GRACE/availability | jq .slots
```

**Expect**: Grace's week holds only Tuesday, Leo's only Saturday, and saving one leaves the other and
the parent's own profile untouched.

### 3.5 Sibling and account isolation (FR-033, FR-036, SC-009)

| Caller | Target | Expect |
|---|---|---|
| Grace (child sign-in) | her own profile, `GET` and `PUT` | `200` |
| Grace | Leo's profile | `404` — not `403` (a sibling is unreachable, not forbidden) |
| Grace | the parent's own profile | `404` |
| A second, unrelated parent | Grace's profile | `404` |
| The parent | Grace's profile `PUT` | `200` — the parent may revise what a child stated |

### 3.6 Profile removal takes its times with it (FR-039)

Remove a child profile that has stated times, then confirm no route returns them and the trainer-side
read 404s.

---

## 4. US5 — A trainer reads stated times

```bash
curl -s -b cookies.txt localhost:8000/api/v1/trainer/coaches | jq '.items[0] | {availability, availability_updated_at}'
curl -s -b cookies.txt localhost:8000/api/v1/trainer/coaches/$COACH/availability | jq
curl -s -b cookies.txt localhost:8000/api/v1/trainer/players/$GRACE/availability | jq
```

**Expect**: the roster row already carries the slots — the list renders "Best times: Mon 4–6pm,
7–9pm" with **no** extra request per row (FR-020, research.md R2-12). The two detail reads return the
full week plus `updated_at`.

**Then check the boundaries** (FR-036, FR-037, SC-009):

| Attempt | Expect |
|---|---|
| Trainer A reads a coach on trainer B's roster | `404` |
| Trainer A reads a player profile with no Active association to them | `404` |
| Trainer A ends an association, then reads that profile's times | `404`, immediately |
| Any `PUT`/`POST`/`DELETE` on a `/trainer/.../availability` path | `405` — no such operation exists in the contract |
| A coach reads another coach's or any player's times | `403`/`404` — a coach sees only their own |

**And the "guidance only" check** (FR-038, SC-011): with a coach who has stated no times at all,
exercise every action that coach can take. **Expect**: nothing is refused, disabled, or delayed on
availability grounds anywhere.

---

## 5. US6 + US7 — Impersonation

### 5.1 Start it (FR-040 – FR-043)

```bash
curl -s -b admin.txt -X POST localhost:8000/api/v1/admin/impersonations \
  -H 'content-type: application/json' -d "{\"user_id\":\"$TRAINER_A\"}" | jq
curl -s -b admin.txt localhost:8000/api/v1/auth/session | jq '{id, role, impersonation}'
```

**Expect**: `201`. The session call now describes **trainer A** — `role: "trainer"`, trainer A's id,
name, and branding — with an `impersonation` block naming both parties and an `expires_at` one hour
out. The same cookie; no second credential was issued.

### 5.2 Exactly the target's permissions, no more (FR-043, SC-016)

```bash
curl -s -b admin.txt localhost:8000/api/v1/admin/users -o /dev/null -w '%{http_code}\n'   # 403
curl -s -b admin.txt localhost:8000/api/v1/trainer/players -o /dev/null -w '%{http_code}\n' # 200
```

**Expect**: `403` on every Super Admin route, `200` on trainer A's own routes — the effective user
*is* trainer A. Walk the UI: the Users nav entry is gone, the trainer's nav is present, and the banner
is on every view (FR-044).

### 5.3 The refusals (FR-042, FR-047, SC-013)

| Attempt | Expect |
|---|---|
| Impersonate another Super Admin | `422 impersonation_not_permitted` |
| Impersonate yourself | `422` |
| Impersonate an erased account | `422` |
| Impersonate an **Inactive** account | `201`, with `target_status_at_start: "inactive"`, labelled in the UI |
| Start a second impersonation from inside one | `403` — the effective user is not a Super Admin |
| Deactivate or erase the impersonated account from inside | `403`, same reason |
| A Trainer or Coach calls `POST /admin/impersonations` | `403`, refused on the request, not by a hidden button |

### 5.4 Exit, and the one asymmetric route (FR-045, R2-15)

```bash
curl -s -b admin.txt -X DELETE localhost:8000/api/v1/admin/impersonations/current -o /dev/null -w '%{http_code}\n'
curl -s -b admin.txt localhost:8000/api/v1/auth/session | jq '{role, impersonation}'
```

**Expect**: `204` — note this succeeded *while the effective user was a Trainer*, which is the whole
point of that route's real-identity gate; then `role: "super_admin"` and `impersonation: null`, with
**no** re-authentication.

### 5.5 The one-hour ceiling (FR-046, SC-014)

Set `IMPERSONATION_MAX_MINUTES=1`, restart, start an impersonation, wait 61 seconds, then make any
request.

**Expect**: the request is already the admin's own; `GET /auth/session` shows
`impersonation: null` and `impersonation_ended.end_reason: "timed_out"`; the UI shows the toast once
(FR-046). The history row has an `ended_at` and a non-null `duration_seconds`. Restore the setting.

### 5.6 The impersonated person is undisturbed (FR-049)

Keep trainer A signed in in a second browser throughout. **Expect**: no sign-out, no interruption, no
notification, and their session's expiry advances only from their own activity.

### 5.7 Dual attribution (FR-052, SC-015)

While impersonating trainer A, change something that writes an audit entry — regenerate the share
link, or end a coach assignment. Then:

```bash
uv run python - <<'PY'
import sqlite3
db = sqlite3.connect("backend/var/app.db")
for row in db.execute("""SELECT action, actor_user_id, impersonator_user_id
                         FROM audit_entries WHERE impersonator_user_id IS NOT NULL
                         ORDER BY occurred_at DESC LIMIT 5"""):
    print(row)
PY
```

**Expect**: the entry names trainer A as `actor_user_id` **and** the Super Admin as
`impersonator_user_id`. No change made under impersonation is attributable to trainer A alone.

### 5.8 The history, and its tamper-proofing (FR-053 – FR-056, SC-017)

```bash
curl -s -b admin.txt "localhost:8000/api/v1/admin/impersonations?target_user_id=$TRAINER_A" \
  | jq '.items[] | {admin: .admin.display_name, target: .target.display_name, started_at, end_reason, duration_seconds}'
curl -s -b cookies.txt localhost:8000/api/v1/admin/impersonations -o /dev/null -w '%{http_code}\n'  # 403
```

**Expect**: every impersonation appears once, with both participants, times, duration, and end reason;
an in-progress one shows `ended_at: null` and `duration_seconds: null`; filtering by admin, by target,
and by date range each returns exactly the matching subset; and any non-Super-Admin gets `403`.

Then prove the triggers (FR-055):

```bash
uv run python - <<'PY'
import sqlite3
db = sqlite3.connect("backend/var/app.db")
for sql in ("DELETE FROM impersonation_sessions",
            "UPDATE impersonation_sessions SET started_at = '2020-01-01'",
            "UPDATE audit_entries SET action = 'nope'",
            "DELETE FROM audit_entries"):
    try:
        db.execute(sql); print("FAIL — not blocked:", sql)
    except sqlite3.IntegrityError as exc:
        print("blocked:", exc)
PY
```

**Expect**: all four blocked. Closing an *open* impersonation row is the one permitted update, which
the service does and the trigger allows.

### 5.9 Erasure and deactivation end it, and the record survives (FR-050, FR-055)

| Event during an impersonation | Expect |
|---|---|
| Another admin erases the target | Ends at once, `end_reason: "target_erased"`; the history row survives and names the account by identifier |
| Another admin deactivates a target that was **Active** at the start | Ends, `target_deactivated` |
| The target was **Inactive** at the start and stays Inactive | Does **not** end — it never left Active (research.md R2-19) |
| The admin's own account is deactivated | Ends, `admin_deactivated` |
| The admin signs out | Ends first as `signed_out`; no session remains that could resume it |
| The admin starts a new impersonation | The previous closes as `superseded`; at most one open per admin |

---

## 6. Quality gates

Every one of these must pass before the feature is mergeable (constitution: Development Workflow).

```bash
# Backend
cd backend
uv run ruff check . && uv run ruff format --check .
uv run mypy src                      # disallow_untyped_defs, warn_return_any
uv run pytest -q                     # unit, integration, contract

# Frontend
cd ../frontend
npm run lint                         # includes eslint-plugin-boundaries (FSD import direction)
npm run typecheck                    # tsc -b --noEmit, zero `any`
npm run test                         # vitest
```

### Feature-specific greps

```bash
cd /d/ai-test-task

# No `any`, anywhere in the new code.
grep -rn ": any\|as any\|<any>" frontend/src && echo "VIOLATION (Principle II)"

# axios only in shared/api.
grep -rn "from 'axios'" frontend/src | grep -v "shared/api" && echo "VIOLATION (Principle IV)"

# No raw SQL in application code. The only permitted literal SQL in this feature is
# revision 0011's CREATE TRIGGER statements, which are not expressible in Core.
grep -rn '\.execute("' backend/src/app && echo "VIOLATION (Principle V)"

# batch_alter_table must never touch audit_entries — it would silently drop the
# append-only triggers (research.md R2-17).
grep -rn "batch_alter_table" backend/migrations/versions/0011_*.py | grep audit_entries \
  && echo "VIOLATION (R2-17)"

# The trainer's identity must never leak through an already-assigned refusal.
grep -rni "already.*assigned" backend/src/app | grep -i "trainer_name\|business_name" \
  && echo "VIOLATION (FR-015, SC-003)"

# Availability must never gate an action: no `if not available` style guard anywhere.
grep -rn "availab" backend/src/app --include=*.py | grep -i "raise \(PermissionDenied\|ActionNotPermitted\)" \
  && echo "VIOLATION (FR-038)"

# Exactly one summary formatter, on the frontend.
test "$(grep -rln 'Best times\|formatAvailabilitySummary' frontend/src | wc -l)" -ge 1 \
  && grep -rn "Best times" backend/src && echo "VIOLATION (R2-12: no server-side formatting)"

# Optional fields declared nullable and rejecting "" (Principle VI).
grep -rn "invitee_name\|message" backend/src/app/schemas/coach_invitation.py | grep -v "min_length=1" \
  | grep "str | None" && echo "CHECK: a nullable string without min_length=1"
```

### Contract check

`backend/tests/contract/test_openapi_contract.py` already compares the live OpenAPI document with
`specs/001-user-roles-admin/contracts/openapi.yaml`. Extend it to also load this feature's
`contracts/openapi.yaml` and assert that every path, method, status code, and required response field
declared at 1.3.0 exists in the running app — the same assertion, over the union of the two files.

### Field-clearing tests (constitution gate)

Every endpoint here that accepts a nullable field needs the two tests the constitution requires:
an explicit `null` clears the column, and an omitted key leaves it unchanged. In this feature that is
`invitee_name` and `message` on invitation issue, and the optional coach profile fields on
registration.

---

## 7. Troubleshooting

| Symptom | Cause |
|---|---|
| Coach registers but lands on default branding | `coach_details.trainer_user_id` not written, or `BrandingService`'s Coach branch still returns the default (research.md R2-06) |
| The old link still works after a resend | The superseding write and the new insert are not in one transaction |
| A week saves but reads back reordered | The read is missing `ORDER BY (day_of_week, start_minute)`; the API contract promises that order |
| A refused save wiped the previous week | Validation is running after the delete instead of before it — this is FR-029's exact failure, and §3.2 is the test for it |
| `403` when exiting an impersonation | The exit route is gated on `require_roles(SUPER_ADMIN)` instead of the real-identity dependency (research.md R2-15) |
| The banner flickers or disappears on navigation | The banner is inside a page rather than `routes/_authed.tsx`, or it is deriving impersonation state client-side |
| A Super Admin's directory page appears inside a trainer's portal | The impersonation mutations are not calling `queryClient.clear()` (frontend-contracts §35) |
| Audit entries carry no impersonator | `get_principal` is not stamping `AsyncSession.info`, or `AuditRepository.add` is not reading it (research.md R2-16) |
| `test_audit_append_only` passes but the triggers are gone | Revision 0011 used `batch_alter_table` on `audit_entries` — the exact trap R2-17 documents. Re-run §1's trigger check |
