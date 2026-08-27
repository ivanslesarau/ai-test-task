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

**Correction (2026-08-26)**: the walkthrough above was performed by hand against a running dev
server, which does not run `tsc`/ESLint and therefore did not surface that the full §6 quality gate
was, at that time, **not** green: `frontend/src/widgets/app-shell/ui/app-shell.tsx` imported
`BackButton` but never rendered it (a JSX comment stood in for the real usage), which failed
`tsc -p tsconfig.app.json --noEmit`, `eslint`, and `npm run build`; `backend/tests/unit/test_settings_validation.py`
read the ambient `backend/.env` instead of being isolated from it, so its two negative-construction
tests could not fail on a machine with a real SMTP relay configured; and SC-013's history-entry half
was asserted only by inspection, not by a test. All three are fixed: the shell now renders a
`BackButton` region per contracts/frontend-contracts.md §7.3 (in addition to, not instead of, the
page-level `BackButton`s from T183–T185), the settings tests construct `Settings(_env_file=None, ...)`
with the relevant `SMTP_*` keys explicitly cleared via `monkeypatch.delenv`, and
`frontend/tests/widgets/user-directory-table.test.tsx` now asserts `router.history.length` is
unchanged by a settled 20-character search term. §6's full gate list — `ruff check`, `ruff format
--check`, `mypy src`, `pytest -q`, `eslint`, a **non-incremental** `tsc --noEmit` (the incremental
`tsc -b` used by `npm run typecheck` can read a stale `.tsbuildinfo` and print nothing even when the
build is broken — `frontend/tsconfig.app.tsbuildinfo` was tracked in git for exactly this reason and
has since been untracked), `npm run test`, and `npm run build` — now passes clean.

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

**Measured** (2026-08-26, this machine, SQLite/WAL, in-process ASGI transport via
`tests/integration/test_extension_timing.py`): accepting a second trainer's invitation
(`POST /join/{code}/accept`, SC-016) completed in **~50 ms**, and switching active context
(`PUT /me/trainer-context`, SC-018) completed in **~15 ms** — both comfortably under their 5 s and
2 s targets. Neither path needed a dedicated index beyond the ones data-model.md §16–§19 already
declare (`ix_tpa_player_status`, `ix_tpa_trainer_status`).

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

---

# Extension validation (2026-08-26): US6, US7, US8

Run after the migrations `0005`–`0007` are applied. The seed path now prints one trainer's standing
join link (data-model §24); without it, obtaining a link means signing in as a trainer first, which
is the loop this walk needs to break.

```bash
cd backend
uv run alembic upgrade head
uv run python -m app.cli seed-demo-trainer        # prints: join URL + trainer credentials
```

## US6 — A Player or Parent Joins Through an Invitation Link

**Setup**: one Trainer with a standing link (from the seed command, or `GET /me/share-link` while
signed in as a trainer).

| # | Action | Expected |
|---|---|---|
| 6.1 | Open `/join/{code}` in a browser with no session | Join page names the trainer's business and shows their branding; registration form offered (FR-073) |
| 6.2 | `GET /api/v1/join/{code}` unauthenticated | 200; body carries **only** business name, branding, and `viewer.state: anonymous` — no trainer id, no contact detail |
| 6.3 | Register with valid detail | 201; `Set-Cookie` present; already signed in; lands in that trainer's context (FR-078) |
| 6.4 | `GET /me/trainers` as the new account | One entry — the link's trainer; `active_trainer_id` matches it |
| 6.5 | Sign in as the trainer, open `/trainer/players` | The new player is on the roster |
| 6.6 | Look in `EMAIL_OUTBOX_DIR` | One confirmation message naming the trainer (FR-079) |
| 6.7 | Register again with the same email | 409 `email_already_registered`, telling the person to sign in and reopen the link (FR-076) |
| 6.8 | Check the database after 6.7 | Exactly one account for that email; no orphan profile, player detail, or association (FR-083) |
| 6.9 | Submit `is_self: true` with a date of birth 12 years ago | 422 with the error on `date_of_birth` — a self-registering player is 18 or over (FR-077) |
| 6.10 | Submit `is_self: false` with a date of birth 30 years ago | 422 on `date_of_birth` — a dependant is 1 to 18 |
| 6.11 | Submit `is_self: false` with no `player_name` | 422 on `player_name` |
| 6.12 | Regenerate the link as the trainer, then open the old code | 404 `invitation_link_invalid` within seconds (SC-020) |
| 6.13 | Check the associations after 6.12 | The player from 6.3 is still on the roster (FR-069) |
| 6.14 | Deactivate the trainer, open their current code | 404, same message and body as 6.12 — the refusal does not say why (FR-070) |
| 6.15 | Request 11 unknown codes from one origin | 11th returns 429 with `Retry-After` (FR-071) |
| 6.16 | Wait out the window, request a valid code | 200 — access resumes with no intervention (SC-021) |

Checking that the refusal discloses nothing (6.14):

```bash
curl -s http://localhost:8000/api/v1/join/definitely-not-a-real-code    > /tmp/a.json
curl -s http://localhost:8000/api/v1/join/{revoked_code}                > /tmp/b.json
diff /tmp/a.json /tmp/b.json && echo "identical — FR-070 holds"
```

The 10,000-attempt guessing trial SC-021 specifies belongs in the integration suite, not in a manual
walk; `tests/integration/test_join_link_throttle.py` runs it against the throttle.

## US7 — Several Trainers, and Switching Between Them

**Setup**: Trainer A and Trainer B, each with a standing link; the player account from US6, already
associated with A.

| # | Action | Expected |
|---|---|---|
| 7.1 | Signed in as the player, open Trainer B's link | Confirm button, not a registration form (`viewer.state: can_join`, FR-080) |
| 7.2 | `POST /join/{codeB}/accept` | 200; association created; `active_trainer_id` is now B |
| 7.3 | Count accounts for that email | Exactly one (FR-085) |
| 7.4 | Open Trainer B's link again | 200 with `already_associated: true`; no second association (FR-082) |
| 7.5 | Compare `use_count` on link B before and after 7.4 | Unchanged (FR-068, FR-082) |
| 7.6 | Sign out, sign back in | Active context is B — the last one used, on a fresh session (FR-086) |
| 7.7 | Sign in on a second browser | Active context is still B (FR-086, "on any device") |
| 7.8 | `PUT /me/trainer-context` naming Trainer A | 200; switcher shows both; every context view now shows A's data only |
| 7.9 | Watch the network panel during 7.8 | The `ctx` query namespace is dropped before the first render; no view shows B's data for any frame (FR-087, R-26) |
| 7.10 | `PUT /me/trainer-context` naming a trainer the player never joined | **404**, not 403 — a 403 would confirm that trainer exists (FR-090) |
| 7.11 | As Trainer A, sweep every trainer-facing response for Trainer B's id or name | Nothing, in any field of any endpoint (FR-090, SC-025) |
| 7.12 | Deactivate Trainer B, reload as the player | B is gone from the switcher; the player is moved to A (FR-089) |
| 7.13 | Deactivate A as well | Switcher gone; the player is told they belong to no trainer — not an error page (FR-089) |
| 7.14 | Reactivate A | A returns to the switcher and becomes the active context |
| 7.15 | Sign in as a Coach and open a player link | 403 `role_cannot_join`; no association written (FR-081) |
| 7.16 | Erase the player (Super Admin), then open Trainer A's roster | The row is still there as "Deleted User"; the roster count is unchanged (FR-091, SC-008) |
| 7.17 | As a player with one trainer, look for the switcher | Not rendered (FR-088) |

Scenario 7.11 is the one to automate rather than eyeball —
`tests/integration/test_trainer_isolation.py` walks every trainer-facing route with a two-trainer
fixture and asserts the other trainer's identifiers appear in no response body. That test **is**
SC-025; the manual check is a spot check.

## US8 — A Trainer Brands Their Portal

**Setup**: Trainer A (branded during this walk), Trainer B (left at defaults), the multi-trainer
player from US7.

| # | Action | Expected |
|---|---|---|
| 8.1 | As Trainer A, open `/trainer/portal` | Branding controls and the invitation link on one page |
| 8.2 | Choose a 500 KB PNG | Previewed in place; **not** applied anywhere until saved (FR-097) |
| 8.3 | Save | Logo appears in the trainer's own header |
| 8.4 | Pick a primary colour | Preview updates live; accents and the gradient follow it on save (FR-098) |
| 8.5 | Upload a 3 MB PNG | 413; the existing logo is untouched (FR-094) |
| 8.6 | Upload a `.pdf` renamed `.png` | 422 — the declared type does not match the decoded content |
| 8.7 | Upload a 1200×1200 PNG | Accepted and fitted to 200×200 without distortion — not refused (FR-096) |
| 8.8 | Upload an SVG containing `<script>alert(1)</script>` | 422; nothing stored (FR-095) |
| 8.9 | Upload an SVG containing `<!DOCTYPE …>` with an entity | 422, refused before parsing (R-27) |
| 8.10 | Upload a clean SVG, then `curl -i` its `/media/branding/{key}` | 200 with `X-Content-Type-Options: nosniff` and the `default-src 'none'` CSP header |
| 8.11 | Inspect the rendered logo element | An `<img>` — never `<object>`, `<embed>`, or inline SVG (R-27) |
| 8.12 | Replace the logo, then request the previous key | 404; the old file is gone from disk (FR-103) |
| 8.13 | `GET /join/{codeA}` with no session | Branding present in the response — the join page is branded before anyone has an account (FR-073) |
| 8.14 | As the multi-trainer player, view Trainer A's context, then switch to B | A's logo and colour, then the platform default; no flash of the wrong identity between them (SC-024) |
| 8.15 | With a coach or player signed in, look for branding settings | Not offered; a direct `PATCH /me/branding` returns 403 (FR-093) |
| 8.16 | Change the colour as Trainer A while a player of A is signed in elsewhere | The player sees the new colour on their next view, without signing out (FR-102, SC-022) |
| 8.17 | Reset | Logo and colour both return to the platform default; the stored file is removed (FR-100) |
| 8.18 | Open `/login` | Platform default branding, never a trainer's (FR-101) |

**Contrast is a unit test, not an eyeball check.** `brandPalette` is pure, so
`frontend/tests/brand-palette.test.ts` sweeps a few hundred colours — including the mid-tone band
where neither black nor white text reaches 4.5:1 against the raw colour — and asserts every returned
text-bearing surface clears 4.5:1. That test is SC-023.

**Known limitation, worth seeing during 8.15**: a Coach signed in today sees the platform default,
not their trainer's branding, because which trainer a coach works for is US-01.08 and does not exist
yet. `branding_service.resolve_for_viewer` carries the branch and a `TODO(US-01.08)`. See
[research.md](./research.md) R-33.

## Cross-cutting checks — extended

| Check | How | Requirement |
|---|---|---|
| No cross-trainer leakage | `tests/integration/test_trainer_isolation.py`, every trainer-facing route, two-trainer fixture | FR-090, SC-025 |
| Code entropy and throttle | `tests/integration/test_join_link_throttle.py`, 10,000-code trial | FR-066, FR-071, SC-021 |
| Contrast across the colour space | `frontend/tests/brand-palette.test.ts` | FR-099, SC-023 |
| Registration atomicity | Force a failure after the account insert; assert nothing persisted | FR-083 |
| SVG screening | Fixture set of hostile SVGs in `tests/unit/test_svg_screening.py` | FR-095 |
| Permission matrix still complete | The existing matrix test gains the join, share-link, branding, context, and roster routes | SC-002 |
| Backfill idempotence | Run `alembic upgrade head` twice; count `share_links` | data-model §23 |

## Quality gates — extended

No new commands. Two greps join the two already in §6:

```bash
# A trainer id arriving as a request parameter — R-25 forbids it; context is server-resolved.
grep -rn "trainer_id" backend/src/app/api/ | grep -v "admin_users_router" | grep "Query\|Path("

# A logo rendered anywhere but an <img>, which R-27's last layer depends on.
grep -rn "branding" frontend/src --include=*.tsx | grep -E "<object|<embed|dangerouslySetInnerHTML"
```

Both should print nothing.
