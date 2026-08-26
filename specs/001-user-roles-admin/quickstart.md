# Quickstart & Validation Guide

**Feature**: `001-user-roles-admin` | **Plan**: [plan.md](./plan.md)

How to bring the feature up locally and prove each user story actually works. Scenario numbers below
match the acceptance scenarios in [spec.md](./spec.md), so a reviewer can walk the spec and this guide
side by side.

This is a run-and-verify guide. Implementation belongs in `tasks.md` and the code itself; nothing here
should be pasted into the application.

---

## 1. Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.13+ | `python --version` |
| Node.js | 22 LTS+ | `node --version` |
| uv *(or pip)* | current | `uv --version` |

No database server, message broker, or mail server is needed. SQLite is a file, and email goes to a
local directory in development (R-11).

---

## 2. Backend setup

```bash
cd backend
uv sync                          # or: python -m venv .venv && pip install -e ".[dev]"
cp .env.example .env             # then edit — see the table below
uv run alembic upgrade head      # creates the SQLite file and all 9 tables
uv run python -m app.cli bootstrap-superadmin   # the only account that cannot be created via the API
uv run uvicorn app.main:app --reload --port 8000
```

**Required environment variables** — all loaded through `pydantic-settings`; the app refuses to start
if any is missing, rather than falling back to a default that would be wrong in production.

| Variable | Example | Notes |
|---|---|---|
| `APP_ENV` | `development` | Selects the email sink and cookie `Secure` policy |
| `DATABASE_URL` | `sqlite+aiosqlite:///./var/app.db` | Must be the async driver |
| `SESSION_COOKIE_NAME` | `pp_session` | |
| `SESSION_IDLE_DAYS` | `7` | FR-011 |
| `INVITATION_TTL_HOURS` | `24` | FR-025 |
| `SIGNIN_MAX_ATTEMPTS` | `10` | SC-011 |
| `SIGNIN_WINDOW_MINUTES` | `15` | SC-011 |
| `UPLOAD_DIR` | `./var/uploads` | R-07 |
| `MAX_UPLOAD_BYTES` | `5242880` | FR-034 |
| `EMAIL_BACKEND` | `filesystem` | `smtp` in production |
| `EMAIL_OUTBOX_DIR` | `./var/outbox` | Where the development sink writes messages |
| `FRONTEND_BASE_URL` | `http://localhost:5173` | Used to build the setup link in the invitation |
| `BOOTSTRAP_ADMIN_EMAIL` | `admin@example.org` | Read only by the bootstrap command |
| `BOOTSTRAP_ADMIN_PASSWORD` | *(≥12 chars)* | Read only by the bootstrap command |

`bootstrap-superadmin` is idempotent and **refuses to run if any Super Admin already exists**, so it
cannot be used to mint a second administrator.

Verify: `http://localhost:8000/docs` lists 19 operations across four tags.

---

## 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env             # VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev                      # http://localhost:5173
```

The dev server proxies `/api` to port 8000 so the session cookie stays first-party — required, because
the cookie is `SameSite=Lax` (R-03). Pointing the frontend at a different origin will appear to work
until sign-in silently fails to persist.

---

## 4. Story-by-story validation

Each block is runnable end to end and maps to one user story's **Independent Test**.

### US1 — Role-Separated Sign-In

**Setup**: the bootstrap Super Admin, plus one account per other role created through US2 below.

| # | Action | Expected |
|---|---|---|
| 1.1 | Sign in as the Super Admin | Admitted; lands on the Super Admin area; `pp_session` cookie set `HttpOnly` |
| 1.2 | Sign in with a wrong password | 401, message identical to that for an unknown email |
| 1.3 | Sign in with an unregistered email | 401, byte-identical body to 1.2 |
| 1.4 | As a Trainer, call `POST /api/v1/admin/users` directly with curl | 403; a `permission_denied` audit entry is written |
| 1.5 | As a Coach, call `GET /api/v1/admin/users/{other_id}` | 403 |
| 1.6 | Sign out, then reuse the old cookie | 401 |
| 1.7 | Fail sign-in 10 times for one email | 11th attempt returns 429 with `Retry-After` |
| 1.8 | Wait out the window, retry with correct credentials | Admitted — no administrative unlock needed (SC-011) |

Checking the cookie flags in 1.1:

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.org","password":"<password>"}' | grep -i set-cookie
# expect: HttpOnly, SameSite=Lax, Path=/
```

**The permission matrix is the highest-risk part of this feature.** The integration suite asserts every
role against every restricted route, which is what SC-002 requires; scenarios 1.4 and 1.5 are spot
checks, not the proof.

### US2 — Super Admin Creates a Trainer Account

| # | Action | Expected |
|---|---|---|
| 2.1 | As Super Admin, create a Trainer with business name, name, email, phone | 201; account Active; `has_password` false; appears in the directory |
| 2.2 | Look in `EMAIL_OUTBOX_DIR` | One message containing a `/set-password?token=…` link and **no password** |
| 2.3 | Open the link, set a 12+ character password | 204; the invitation is consumed |
| 2.4 | Sign in as the new Trainer | Admitted; lands on the Trainer area |
| 2.5 | Open the same link again | 410, `invitation_not_usable` |
| 2.6 | Create another account with the same email | 409, `email_already_registered`; no partial account created |
| 2.7 | Submit a malformed phone and a blank last name together | 422 listing **both** fields, not one generic error (FR-022) |
| 2.8 | As a Trainer, attempt to create a user | 403 |
| 2.9 | Create a Coach and a Player/Parent account | Both created and invited by the same flow, holding no trainer relationship (FR-030) |
| 2.10 | Read `GET /admin/users/{id}/audit` | `user_created` and `invitation_issued` entries naming the acting Super Admin |
| 2.11 | Set a password shorter than 12 characters | 422 with a `password` field error |
| 2.12 | Try `password123456` (in the breached list) | 422 with a `password` field error |

Scenario 2.9 is what makes US3 through US5 demonstrable across all four roles — create these accounts
before validating the later stories.

### US3 — Any User Edits Their Own Profile

Run this **once per role**; the role detail block differs each time.

| # | Action | Expected |
|---|---|---|
| 3.1 | `GET /me/profile` as each role | 200; `editable_fields` lists exactly that role's editable fields |
| 3.2 | Change first name, last name, phone; save | 200; values persist across sign-out and back in |
| 3.3 | Upload a 200 KB PNG | 200; both `photo_url` and `thumbnail_url` returned and fetchable |
| 3.4 | Upload a 6 MB image | 413; the previous photo is unchanged |
| 3.5 | Rename a `.txt` file to `.jpg` and upload | 415 — validation decodes the bytes, ignoring the extension (R-07) |
| 3.6 | Replace an existing photo, then look in `UPLOAD_DIR` | The previous original and thumbnail are gone |
| 3.7 | As a Player/Parent, set school and jersey number | 200 |
| 3.8 | As a Coach, set bio, credentials, certifications, public visibility | 200 |
| 3.9 | As a Trainer, set business name, address, website, description | 200 |
| 3.10 | `PATCH /me/profile` with `{"email":"new@x.com"}` | 422 — rejected, not silently ignored (FR-033) |
| 3.11 | `PATCH /me/profile` with `{"skill_level":"Elite"}` | 422 (FR-007) |
| 3.12 | `PATCH` with a Coach session sending `jersey_number` | 422 — the field is not editable for that role |
| 3.13 | As a Coach, `GET /admin/users/{other_id}` | 403 (FR-017) |

### US4 — Deactivate and Reactivate

**Setup**: a Trainer account with a live session in a second browser profile.

| # | Action | Expected |
|---|---|---|
| 4.1 | Deactivate the Trainer as Super Admin | Confirmation required; status becomes Inactive |
| 4.2 | Sign in as that Trainer | 403, `account_not_active`, message naming support |
| 4.3 | Act on the second browser's still-open session | 401 within one minute; session revoked (SC-007) |
| 4.4 | Read the directory filtered to Inactive | The account appears, marked inactive (FR-039) |
| 4.5 | Compare a reporting total before and after | Numerically identical (FR-039, SC-008) |
| 4.6 | Reactivate | Status Active; sign-in works with the **existing** password |
| 4.7 | As a Trainer, attempt to deactivate anyone | 403 |
| 4.8 | As the only Super Admin, deactivate yourself | 422, `self_action_forbidden` |
| 4.9 | Create a second Super Admin, then deactivate the first as the second | 200 — two active admins existed, so one remains after |
| 4.10 | Send a `version` one behind the current value | 409, `stale_version` |
| 4.11 | Deactivate an already Inactive account | 422 — no second deactivation record |
| 4.12 | Read the audit trail | `user_deactivated` and `user_reactivated` entries with actor and time |

**On the last-active-admin guard (FR-041) and why 4.9 succeeds**: whoever is authenticated to call
the deactivate endpoint is themselves an active Super Admin, so `count_active_super_admins()` is
always at least 2 whenever the actor differs from the target — deactivating either one then
legitimately leaves one behind. A distinct actor can only face a target that is the *sole* active
Super Admin through a concurrent request racing another deactivation, which is exactly why R-09
requires the count-then-write to happen inside one transaction rather than through a scenario a
manual click-through can reproduce. The self-action case (4.8) is the one path to this guard that
*is* reachable through the running application; the non-self path is covered by a direct service-level
test instead (`tests/integration/test_admin_guards_api.py`).

### US5 — Erase a User's Personal Information

**Setup**: an account with a photo, at least one audit entry, and — once later epics exist —
attendance and payment history.

| # | Action | Expected |
|---|---|---|
| 5.1 | Erase with a stated reason | Prominent warning; 200; the response already shows anonymized values |
| 5.2 | Erase without a reason | 422 (FR-044) |
| 5.3 | Read the account | Name `Deleted User`; email `deleted_{id}@example.com`; phone null; photo null |
| 5.4 | Look in `UPLOAD_DIR` | Both image files removed |
| 5.5 | Sign in with the former credentials | 401 |
| 5.6 | Attempt to reactivate | 422, `erasure_is_permanent` |
| 5.7 | `PATCH /me/profile` on a session held before erasure | 401 — sessions were revoked |
| 5.8 | Search the directory for the former name or email | No match (SC-009) |
| 5.9 | Read historical records referencing the account | Still present, attributed to `Deleted User`, original dates and amounts |
| 5.10 | Compare reporting totals before and after | Numerically identical (SC-008, FR-047) |
| 5.11 | Create a new account with the former email | 201 — the address was released (FR-050) |
| 5.12 | Create an account with email `deleted_x@example.com` | 422 — the placeholder pattern is reserved |
| 5.13 | `GET /admin/erasure-records/{id}` as Super Admin | Original email, name, actor, reason, timestamp |
| 5.14 | The same call as a Trainer | 403 |
| 5.15 | Erase yourself as the only active Super Admin | 422, `self_action_forbidden` — see the note on US4's 4.8/4.9 for why the non-self `last_super_admin` path isn't reachable through the running application either |

Scenario 5.10 is the one that most often fails in practice. Capture the totals **before** erasing —
once erased, there is no way back to compare against.

### US2/US3 re-walk after the bug-fix slice (2026-08-25)

Re-run against the fixes in tasks.md's `## Fixes` section, by hand against a running server, to
confirm no divergence from the table above:

| # | Action | Observed |
|---|---|---|
| 2.6 | Create a Trainer, then create another account with the same email | 201, then 409 `email_already_registered` — unchanged |
| 2.7 | Submit a malformed phone and a blank last name together | 422 naming both `phone` and `last_name` — the phone check is new (T167); it did not fire before this slice |
| 3.2 (extended) | `PATCH /me/profile` with an optional field set, then cleared with `null`, then resubmitted as `""` | Set: 200; cleared: 200 with the field `null` in the response; `""`: 422 naming the field — the last two cases are new (T163–T166); previously `""` was accepted and persisted as an empty string |
| 3.3 | Upload a photo, then fetch the returned `photo_url` with the session cookie | 200; the URL is API-relative and requires the auth cookie the same way every other admin/profile endpoint does — this is why the frontend must resolve it through `resolveMediaUrl` before use in an `<img>` (T159, T176) rather than pass it through unresolved |
| 3.5 | Rename a `.txt` file to `.jpg` and upload | 415 — unchanged; still decodes bytes rather than trusting the extension or claimed content type |

The directory search debounce (FR-063, SC-013) and back-navigation restoring the directory's filters
(FR-061) are frontend-only behaviors with no curl equivalent; they are exercised end to end against
the real router and real component tree — not mocked — by
`frontend/tests/widgets/user-directory-table.test.tsx` and `frontend/tests/shared/back-button.test.tsx`
respectively. Both passed as of this walkthrough.

No divergence found between this table and the documented behaviour above it, once the bug-fix slice
is applied.

---

## 5. Cross-cutting checks

| Check | How | Requirement |
|---|---|---|
| No internal detail leaks | Stop the database mid-request; force a constraint violation | FR-056, SC-012 |
| Audit trail is append-only | Attempt `UPDATE audit_entries` directly in the SQLite file | FR-055 |
| Directory performance | Seed 10,000 accounts; time the first filtered page | SC-006 |
| Contract has not drifted | The contract test compares the generated OpenAPI to `contracts/openapi.yaml` | — |
| No `any` on the frontend | `npm run typecheck` plus the lint rule | Constitution II |
| FSD import direction | The lint boundaries rule | Constitution IV |

Seeding for the performance check:

```bash
uv run python -m app.cli seed-users --count 10000 --roles player_parent,coach,trainer
time curl -s -b cookies.txt \
  'http://localhost:8000/api/v1/admin/users?page=1&page_size=25&status=active&role=player_parent' \
  -o /dev/null
# expect well under 3 s (SC-006)
```

**Measured** (2026-08-19, this machine, SQLite/WAL, 10,001 accounts total — 10,000 seeded plus the
bootstrap Super Admin): a role-and-status-filtered first page returned in **~0.22–0.25 s** across
three consecutive requests, an unfiltered first page in ~0.22 s, and a name/email search in ~0.23 s
— all comfortably under the 3 s target, with no index or query changes needed beyond the
`(status, role)` and `created_at` indexes already in `data-model.md` §2.

---

## 6. Quality gates

The commands `tasks.md` attaches to each slice. All must pass before a slice is done.

```bash
# Backend
cd backend
uv run ruff check . && uv run ruff format --check .
uv run mypy src                       # strict; no untyped defs
uv run pytest -q                      # unit + integration + contract
uv run pytest -q tests/integration/test_permission_matrix.py   # SC-002 — every role × every route

# Frontend
cd frontend
npm run lint
npm run typecheck                     # tsc --noEmit, strict, zero `any`
npm run test
```

Two greps that catch the constitution's most-violated rules faster than a full run:

```bash
# Any raw SQL outside the two documented exceptions (plan.md §Complexity Tracking).
# Matches a literal-string .execute("...") call — not Path.read_text()/write_text(),
# which an earlier, looser version of this grep matched by mistake.
grep -rn '\.execute("' backend/src/app --include=*.py | grep -v "db/engine.py"

# axios imported anywhere but shared/api
grep -rn "from 'axios'" frontend/src | grep -v "shared/api"
```

Both should return nothing.

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Sign-in succeeds, next request is 401 | Frontend on a different origin, so the `SameSite=Lax` cookie is dropped | Use the Vite proxy; do not point at `http://127.0.0.1:8000` while the app runs on `localhost` |
| `FOREIGN KEY constraint failed` never fires | Pragmas not applied on this connection | Check the connect event in `db/engine.py`; SQLite disables foreign keys per connection by default |
| `database is locked` under concurrent writes | WAL or busy timeout not set | Verify both pragmas; SQLite allows one writer (plan.md §Constraints) |
| No invitation email | `EMAIL_BACKEND=filesystem` writes to disk, it does not send | Look in `EMAIL_OUTBOX_DIR` |
| shadcn CLI writes to `src/components/ui` | `components.json` not pointing at `shared/ui` | Fix the aliases — the default path violates constitution IV |
| Alembic autogenerate produces an empty revision | Models not imported in the migration environment | Import the model modules in `migrations/env.py` |
