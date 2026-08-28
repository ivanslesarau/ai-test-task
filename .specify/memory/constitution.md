<!--
SYNC IMPACT REPORT
==================
Version change: 1.1.0 -> 1.1.1
Bump rationale: PATCH. Corrects a stale statement of fact — the sync-impact report's
  TODO(NULL_NORMALIZATION_HELPER) said the frontend had no shared empty-string-to-null helper. It
  has had one since D-01: `frontend/src/shared/lib/normalize-payload.ts`, the single normalizer
  every TanStack Form submit handler routes through, covered by
  `frontend/tests/shared/normalize-payload.test.ts`. The bug-fix slice recorded this as discharged
  in its own tasks.md, but the constitution's own text was never updated — leaving the TODO in
  place taught the next reader that Principle VI was unimplemented when it is not. No principle,
  obligation, or section changed; only this correction.

Modified principles: none.

Added sections: none.

Removed sections: none.

Follow-up TODOs:
  - TODO(NULL_NORMALIZATION_HELPER): removed — discharged by D-01;
    `frontend/src/shared/lib/normalize-payload.ts` is the single normalizer Principle VI requires.
  - TODO(CHART_LIBRARY): Chart.js is designated for dashboard visualizations but is not yet an
    installed dependency, since no dashboard epic has been implemented. Recorded as a pinned
    forward decision, not as as-built state.
-->

# PracticePerfect Constitution

## Core Principles

### I. Spec-Driven Development (NON-NEGOTIABLE)

Work MUST flow through the pipeline Specification -> Plan -> Tasks -> Code. No functional code may
be written, and no dependency added, before `spec.md`, `plan.md`, and `tasks.md` exist for that
feature and have been approved. `spec.md` MUST describe business outcomes only and MUST NOT name
libraries, tables, endpoints, or file layouts; those belong in `plan.md`. Tasks MUST be executed in
their declared dependency order and checked off as they complete.

Rationale: The specs in `Task/Epics/` define eight interdependent epics. Code written ahead of an
approved plan produces architecture that cannot absorb the next epic without rework.

### II. End-to-End Type Safety (NON-NEGOTIABLE)

- Frontend: TypeScript runs in strict mode. The `any` type MUST NOT appear anywhere — not in
  components, props, hooks, store slices, route definitions, or API response models. Genuinely
  dynamic values MUST be typed `unknown` and narrowed through explicit type guards.
- Backend: Every function signature, attribute, and return value MUST carry a type hint. All
  request, response, and internal data-transfer models MUST be Pydantic V2 models; validation and
  serialization MUST go through Pydantic rather than hand-written dict manipulation.
- Boundary parity: Client-side API response types MUST mirror the backend Pydantic schemas, and
  form validation schemas MUST encode the same constraints the backend enforces. Optionality is
  part of that parity and is governed by Principle VI.

Rationale: `any` and untyped dicts defer contract breaks to runtime, where a multi-role permission
system fails as data leakage instead of as a compile error.

### III. Layered Backend Architecture

Backend code MUST separate into exactly three layers with a one-way dependency flow
(router -> service -> repository):

- **Routers/Endpoints**: HTTP concerns only — request parsing, Pydantic input validation, status
  codes, response models. MUST NOT contain business rules or database queries.
- **Services**: All business logic, authorization decisions, and orchestration. MUST NOT touch
  `Request`/`Response` objects and MUST NOT emit queries directly.
- **Repositories**: All database access and query construction. MUST NOT contain business rules.

Dependencies — database sessions, services, settings — MUST be supplied through FastAPI `Depends`.
Mutable global or module-level state MUST NOT be used to carry request-scoped data.

Rationale: Business rules reachable only through an HTTP handler cannot be unit-tested or reused by
background jobs, and shared global state breaks under async concurrency.

### IV. Feature-Sliced Frontend Architecture

The frontend MUST follow Feature-Sliced Design with the layers `app`, `processes`, `pages`,
`widgets`, `features`, `entities`, `shared`. Imports MUST only point downward through that order;
cross-imports between slices of the same layer are forbidden — promote shared code to a lower layer
instead.

- **UI**: All `shadcn/ui` primitives and generic Tailwind components MUST live in `shared/ui`.
  Feature-specific composition happens in `features`/`widgets` and consumes `shared/ui`.
- **API**: The `axios` instance and all interceptors MUST be defined once in `shared/api`. UI
  components MUST NOT call `axios` directly.
- **Server state**: TanStack Query owns ALL server state. Query and mutation hooks MUST be defined
  in the `entities` or `features` slice that owns the domain object, with explicit query keys.
- **Client state**: Zustand is permitted ONLY for global client-side UI state (modals, theme,
  sidebar, wizard progress). Server responses MUST NOT be copied into a Zustand store.
- **Routing**: Route params and search params MUST use TanStack Router's typed definitions with
  runtime validation; string-built URLs and untyped param reads are forbidden.
- **Forms**: Forms MUST use TanStack Forms with a Zod schema whose rules match the backend
  constraints for the same fields.

Rationale: One owner per kind of state eliminates the stale-data and cache-invalidation class of
bugs, and FSD's one-way imports keep eight epics from fusing into one inseparable module.

### V. Async-First Persistence & Contained Failures

- All I/O paths MUST be `async`/`await`. Database work MUST use SQLAlchemy `AsyncSession`; blocking
  calls MUST NOT run on the event loop.
- All queries MUST be expressed with SQLAlchemy 2.0 ORM or Core constructs. Raw SQL strings and
  string-interpolated query fragments MUST NOT be used.
- Exceptions MUST be caught in the service layer and translated into domain errors that routers
  raise as explicit `HTTPException`s with a stable response shape. Database errors, driver
  messages, ORM tracebacks, and stack traces MUST NEVER reach the client; full detail goes to the
  server log.

Rationale: Sync calls on the event loop serialize the entire API under load, and leaked driver
errors expose schema internals to unauthenticated callers.

### VI. Null-Not-Empty Data Contract (NON-NEGOTIABLE)

An absent optional value is spelled `null` at every layer. The empty string is a rendering artifact
of React controlled inputs; it MUST NOT cross the network boundary and MUST NOT reach a database
column.

- **Frontend — payload normalization**: React controlled inputs initialize optional fields to `""`.
  Every TanStack Form submit handler MUST pass its values through the single shared normalization
  helper in `shared/lib` before the payload reaches `axios`. That helper MUST convert any string
  that is empty or contains only whitespace to `null`, recursing through nested objects and arrays.
  Values that are not empty-or-whitespace strings MUST pass through unchanged; trimming of real
  values, if wanted, belongs in the field's Zod schema, not in the normalizer. Per-form ad-hoc
  conversion, inline ternaries at the call site, and duplicate helpers are forbidden — there is
  exactly one normalizer. An empty string MUST NOT be sent to the backend for an optional field
  under any circumstance.
- **Backend — nullable schemas are explicit**: Pydantic schemas MUST declare nullable fields as
  `str | None` (equivalently `Optional[str]`). A bare `str` field standing in for a nullable column,
  or optionality implied only by a default, is a violation. A nullable string field MUST also reject
  the empty string — constrain it with `min_length=1` so `""` returns a 422 validation error instead
  of being persisted.
- **Backend — an explicit null clears the value**: Update schemas (PATCH/PUT) MUST distinguish an
  omitted field from a field explicitly set to `null`. Services MUST read submitted fields via
  `model_dump(exclude_unset=True)`. A key present with value `None` MUST propagate to the
  repository, which MUST assign `None` to the mapped attribute so the column becomes SQL `NULL`.
  Repositories MUST NOT skip `None` values, coerce them to `""`, or retain the previous value. Keys
  absent from the payload MUST leave their columns untouched.
- **Storage invariant**: No nullable text column may hold `""`. Data arriving from any other source
  — imports, seeds, migrations, CLI commands — MUST be normalized to `null` at its entry boundary.

Rationale: Two spellings of "no value" force every downstream reader — query filters, dashboard
aggregates, `COALESCE`, and every `if (!value)` check — to handle both, and the two spellings
diverge silently. Worse, without the `exclude_unset` distinction a user cannot clear an optional
field at all: the API accepts the request and reports success while the old value stays in the
database.

## Technology Stack & Constraints

The stack below is the ratified initial stack. Versions are minimum floors. Adding, replacing, or
removing an entry — or raising a major version — requires a constitution amendment.

**Backend (ratified initial stack)**: Python >= 3.13; FastAPI >= 0.115 on uvicorn[standard] >= 0.32;
SQLAlchemy >= 2.0.36 async with aiosqlite >= 0.20 over SQLite; Alembic >= 1.14 for migrations;
Pydantic >= 2.9 with pydantic-settings >= 2.6 and email-validator >= 2.2; pwdlib[argon2] >= 0.2.1
for password hashing; python-multipart >= 0.0.12 and pillow >= 11.0 for uploads and image
processing; aiosmtplib >= 3.0 for outbound mail; phonenumbers >= 8.13 for phone validation.

**Frontend (ratified initial stack)**: TypeScript >= 5.7 in strict mode on React >= 19, built by
Vite >= 6; TanStack Router >= 1.87, TanStack Query >= 5.59, TanStack Form
(`@tanstack/react-form`) >= 1.0; Zod >= 3.23 for schemas; Zustand >= 5 for client UI state; axios
>= 1.7 for transport; Tailwind CSS >= 4 via `@tailwindcss/vite` with shadcn/ui over `radix-ui`,
plus `class-variance-authority`, `clsx`, `tailwind-merge`, and `lucide-react`; `next-themes` for
theme state and `sonner` for toasts.

**Tooling & tests (ratified initial stack)**: Backend — ruff >= 0.7 (line length 100, target
py313), mypy >= 1.13 with `disallow_untyped_defs` and `warn_return_any` enabled, pytest >= 8.3 with
pytest-asyncio in auto mode, httpx >= 0.27. Frontend — ESLint >= 9 with typescript-eslint and
`eslint-plugin-boundaries` enforcing FSD import direction, vitest >= 3.2 with jsdom, Testing
Library, and msw >= 2.6 for HTTP mocking.

Additional constraints:

- **Configuration**: Every configurable value — database URL, JWT secret, API keys, CORS origins,
  feature toggles — MUST be read from environment variables through a `pydantic-settings` settings
  class injected via `Depends`. Secrets MUST NOT be hard-coded or committed, and a `.env.example`
  listing every required key MUST be kept current.
- **Charts**: Dashboard visualizations MUST use Chart.js behind a typed `shared/ui` wrapper
  component; chart datasets MUST be derived from TanStack Query data, never from a Zustand store.
  Chart.js is a pinned forward decision and is not yet installed — the epic that introduces
  dashboards adds it without a further amendment.
- **Design tokens**: Styling MUST use the tokens in `Task/designs/DESIGN_TOKENS.md` through Tailwind
  configuration and CSS custom properties. Ad-hoc hex colors, font sizes, and spacing values in
  components are forbidden.
- **Migrations**: Schema changes MUST ship as versioned Alembic migrations reviewed alongside the
  code that requires them. Editing a database by hand is not a schema change.

## Development Workflow & Quality Gates

1. Every feature starts from an epic in `Task/Epics/` and proceeds through `/speckit-specify`,
   `/speckit-plan`, `/speckit-tasks`, then `/speckit-implement`.
2. A change is mergeable only when all gates pass:
   - Backend: mypy clean under the configured strict flags; ruff clean; no raw SQL; no sync DB
     calls; layer boundaries respected.
   - Frontend: `tsc -b --noEmit` clean with zero `any`; ESLint clean, including the boundaries rule.
   - Nullable fields: every new or changed optional field declares `str | None` with `min_length=1`,
     and every TanStack Form submit path routes through the shared normalizer (Principle VI).
   - Field clearing: any endpoint accepting a nullable field MUST have a test that sends an explicit
     `null` and asserts the persisted column is `NULL` afterwards, plus a test that omits the key
     and asserts the column is unchanged.
   - Tests covering the acceptance criteria of the implemented tasks pass.
3. Reviews MUST verify constitution compliance explicitly, not only correctness. A reviewer who
   finds a violation MUST block the change or record an approved exception (see Governance).
4. Any deviation from a principle MUST be justified in the change description, naming the simpler
   compliant alternative that was rejected and why. "Faster to write" is not a justification.
5. Tasks MUST be checked off in `tasks.md` as they land, so the plan remains an accurate record of
   what exists.

## Governance

This constitution supersedes all other development practices, habits, and conventions. Where a tool
default, tutorial, or generated scaffold conflicts with it, this document wins.

**Amendment procedure**: An amendment MUST be proposed as a change to this file stating the
motivation, the principles affected, and the migration path for code that already violates the new
rule. It takes effect only once approved by the project maintainer and merged.

**Versioning policy**: This document follows semantic versioning.

- MAJOR: a principle is removed, or redefined so that currently compliant code becomes violating.
- MINOR: a new principle or section is added, or existing guidance is materially expanded.
- PATCH: clarifications, rewording, and typo fixes that change no obligation.

**Compliance review**: Compliance is checked at every code review and at the end of every
`/speckit-implement` run. Exceptions are granted per-change and never stand indefinitely: each MUST
be recorded with its scope plus a follow-up task to remove it, and an exception that outlives two
features MUST be resolved either by fixing the code or by amending this constitution.

**Runtime guidance**: `CLAUDE.md` carries day-to-day operating instructions and MUST stay consistent
with this constitution; if the two disagree, this constitution governs and `CLAUDE.md` MUST be
corrected.

**Version**: 1.1.1 | **Ratified**: 2026-08-19 | **Last Amended**: 2026-08-28
