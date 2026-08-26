# PracticePerfect API

FastAPI + SQLAlchemy 2.0 (async) + SQLite backend for user roles, authorization, and Super Admin
user management (feature `001-user-roles-admin`). See
`../specs/001-user-roles-admin/` for the spec, plan, data model, and API contract this code
implements, and `../specs/001-user-roles-admin/quickstart.md` for the full scenario-by-scenario
validation walkthrough.

## Setup

Requires Python 3.13+.

```bash
cd backend
uv sync                          # or: python -m venv .venv && pip install -e ".[dev]"
cp .env.example .env             # then edit — see Environment variables below
uv run alembic upgrade head      # creates the SQLite file and all 9 tables
uv run python -m app.cli bootstrap-superadmin   # the only account that cannot be created via the API
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

## Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Tests are organized under `tests/unit/`, `tests/integration/`, and `tests/contract/` (the latter
diffs the generated OpenAPI schema against `specs/001-user-roles-admin/contracts/openapi.yaml`).
