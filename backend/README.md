# PracticePerfect API

FastAPI + SQLAlchemy 2.0 (async) + SQLite backend implementing Epic-01 in full, across two features:

- `001-user-roles-admin` — user roles, authorization, Super Admin management, ShareLink onboarding,
  multi-trainer association, portal branding, and parent/child family accounts. See
  `../specs/001-user-roles-admin/`.
- `002-coach-availability-impersonation` — coach invitations, weekly availability ("My Times") for
  coaches and player profiles, and Super Admin impersonation. See
  `../specs/002-coach-availability-impersonation/`.

Each feature's directory holds its own spec, plan, data model, and API contract, and its own
`quickstart.md` with the full scenario-by-scenario validation walkthrough.

## Setup

Requires Python 3.13+.

```bash
cd backend
uv sync                          # or: python -m venv .venv && pip install -e ".[dev]"
cp .env.example .env             # then edit — see Environment variables below
uv run alembic upgrade head      # creates the SQLite file and all 19 tables
uv run python -m app.cli bootstrap-superadmin   # the only account that cannot be created via the API
uv run python -m app.cli seed-demo-trainer      # a Trainer with a printed join URL, for testing US6 locally
uv run uvicorn app.main:app --reload --port 8000
```

`bootstrap-superadmin` is idempotent and refuses to run if any Super Admin already exists, so it
cannot be used to mint a second administrator.

## Environment variables

All configuration is loaded through `pydantic-settings` (`src/app/core/config.py`); the app refuses
to start if any required key is missing rather than falling back to a default that would be wrong in
production. See `.env.example` for the full list with example values:

| Variable | Notes |
|---|---|
| `APP_ENV` | Selects the email sink and cookie `Secure` policy |
| `DATABASE_URL` | Must be the async driver (`sqlite+aiosqlite://...`) |
| `SESSION_COOKIE_NAME`, `SESSION_IDLE_DAYS` | Opaque session cookie lifetime |
| `INVITATION_TTL_HOURS` | Credential-setup invitation expiry |
| `SIGNIN_MAX_ATTEMPTS`, `SIGNIN_WINDOW_MINUTES` | Sign-in rate limiting |
| `UPLOAD_DIR`, `MAX_UPLOAD_BYTES` | Profile photo storage |
| `EMAIL_BACKEND`, `EMAIL_OUTBOX_DIR` | `filesystem` in development, `smtp` in production |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS` | `SMTP_HOST` and `SMTP_FROM_ADDRESS` become mandatory the moment `EMAIL_BACKEND=smtp` — the app refuses to start without them, rather than turning every invitation into a swallowed exception |
| `SMTP_TLS` | `starttls` (587, the default) \| `implicit` (465) \| `none` (a local dev sink such as Mailpit/MailHog on 1025) |
| `SMTP_TIMEOUT_SECONDS` | Connection timeout for the SMTP sender; default `10` |
| `FRONTEND_BASE_URL` | Used to build links in outgoing email and for CORS |
| `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD` | Read only by the `bootstrap-superadmin` CLI command, never by the API |
| `COACH_INVITATION_TTL_DAYS` | Feature 002. How long a coach invitation stays usable (FR-002) |
| `IMPERSONATION_MAX_MINUTES` | Feature 002. The impersonation ceiling, enforced on read rather than by a scheduler (FR-046, research.md R2-19) |

## Architecture

Every request flows through three strictly separated layers (constitution Principle III):

- **Routers** (`src/app/api/v1/`) — HTTP concerns only: request/response models, status codes,
  reading the authenticated user via `Depends`. No business logic and no direct database access.
- **Services** (`src/app/services/`) — all business logic, transaction boundaries, and the
  translation from domain errors (`src/app/core/errors.py`) to what the router reports. Services
  never import FastAPI or raise HTTP exceptions directly.
- **Repositories** (`src/app/repositories/`) — the only layer that talks to SQLAlchemy. No raw SQL
  strings anywhere in this layer; ORM/Core constructs only.

Dependencies are wired exclusively through FastAPI's `Depends` (`src/app/core/deps.py`) — there is no
module-level global state to reach for instead.

Two deliberate, documented exceptions to the "no raw SQL" rule exist, both because no ORM/Core
equivalent exists for them:

- `src/app/db/engine.py` — the `PRAGMA foreign_keys/journal_mode/busy_timeout` connection setup.
- `backend/migrations/versions/0004_create_audit_and_erasure.py` — the `CREATE TRIGGER` statements
  that make `audit_entries` append-only at the database level, as defense in depth alongside the
  audit repository exposing no update/delete method.

A CI check (`.github/workflows/ci.yml`) greps for any raw `.execute("...")` call outside
`db/engine.py` and fails the build if one is found.

## Extension (2026-08-26): ShareLink onboarding, multi-trainer, branding

Three rules a contributor touching this code must know, argued in full in
`../specs/001-user-roles-admin/research.md` R-21 – R-33:

- **A ShareLink's `code` is stored in clear, not hashed** — unlike every other token in this
  codebase (sessions, setup invitations). The trainer must be able to read it back at any time
  (`GET /me/share-link`), and the link is designed to be published on a flyer. Do not "fix" this to
  match the other tokens' hashing pattern.
- **No endpoint accepts a `trainer_id` request parameter to select context.** A Player/Parent's
  active trainer is resolved server-side, on their own account, through
  `core/deps.py::get_trainer_context` / `TrainerContextService.resolve_active_trainer_id`. A CI
  check greps for this outside `admin_users_router` and fails the build if one appears.
- **A trainer's portal logo is served unauthenticated** at `GET /media/branding/{key}` — unlike
  profile photos — because the public join page must show a trainer's branding before anyone has an
  account (FR-073). SVG uploads are screened in `services/svg_screening.py` (stdlib only, no new
  dependency) and served with `X-Content-Type-Options: nosniff` and a locked-down CSP; the frontend
  must render every logo through `<img>` only, never `<object>`/`<embed>`/inline SVG. A second CI
  check greps for that.

`FR-101`'s promise that a trainer's branding reaches their coaches is implemented as of feature 002:
`services/branding_service.py::resolve_for_viewer`'s Coach branch resolves the assigned trainer's
branding through `coach_details.trainer_user_id`, falling back to the platform default for a coach
on no roster (research.md R2-06).

## Extension (2026-08-28): coach invitations, availability, impersonation (feature 002)

Three rules a contributor touching this code must know, argued in full in
`../specs/002-coach-availability-impersonation/research.md`:

- **Coach invitations are a dedicated, hashed-token table (`coach_invitations`), not a second
  `ShareLinkKind`.** `share_links.code` is stored in clear on purpose (R-21); a coach invitation is a
  single-use secret mailed to one named person, and its refusal policy — naming the address it was
  issued for — is the opposite of a `ShareLink`'s uniform, non-disclosing refusal (R2-01).
- **Impersonation creates no second session.** The admin's own `sessions` row gains a nullable
  `impersonation_id` pointer, and exactly one dependency — `core/deps.py::get_principal` — resolves
  the effective caller for every existing and future endpoint (R2-14). `get_current_user` is a
  one-line wrapper over it; do not add impersonation-specific branching anywhere else. The route that
  exits an impersonation authorizes on the caller's *real* identity
  (`get_real_admin_with_open_impersonation`), never `require_roles(SUPER_ADMIN)` — while
  impersonating anyone but another Super Admin, the effective user fails that gate, which would lock
  the admin inside the impersonation until the one-hour ceiling instead of letting them leave (R2-15).
- **`audit_entries` must only ever be altered with plain `op.add_column`, never
  `op.batch_alter_table`.** Alembic's SQLite batch mode recreates the table, which silently drops the
  append-only triggers `0004_create_audit_and_erasure.py` installed — a trap revision
  `0011_coach_invitations_availability_impersonation.py` documents inline and
  `test_migration_0011.py::test_revision_0004_audit_triggers_survive_the_column_addition` guards
  against (R2-17).

## Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Tests are organized under `tests/unit/`, `tests/integration/`, and `tests/contract/` (the latter
diffs the generated OpenAPI schema against the union of both features' `contracts/openapi.yaml`
files).
