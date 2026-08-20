<!--
SYNC IMPACT REPORT
==================
Version change: TEMPLATE (unfilled placeholders) -> 1.0.0
Bump rationale: Initial ratification. The prior file was the unfilled core scaffold with no
  concrete governance, so this is an initial adoption rather than an amendment.

Modified principles (placeholder -> concrete):
  - [PRINCIPLE_1_NAME] -> I. Spec-Driven Development (NON-NEGOTIABLE)
  - [PRINCIPLE_2_NAME] -> II. End-to-End Type Safety (NON-NEGOTIABLE)
  - [PRINCIPLE_3_NAME] -> III. Layered Backend Architecture
  - [PRINCIPLE_4_NAME] -> IV. Feature-Sliced Frontend Architecture
  - [PRINCIPLE_5_NAME] -> V. Async-First Persistence & Contained Failures

Added sections:
  - Technology Stack & Constraints (fills [SECTION_2_NAME]/[SECTION_2_CONTENT])
  - Development Workflow & Quality Gates (fills [SECTION_3_NAME]/[SECTION_3_CONTENT])
  - Governance (concrete amendment, versioning, and compliance rules)

Removed sections: none. Heading hierarchy preserved from the resolved template.

Follow-up TODOs: none. All placeholder tokens resolved.
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
  form validation schemas MUST encode the same constraints the backend enforces.

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

## Technology Stack & Constraints

The stack is fixed. Adding, replacing, or removing an entry requires a constitution amendment.

**Backend**: Python, FastAPI, SQLAlchemy 2.0 (async), SQLite, Pydantic V2, pydantic-settings.

**Frontend**: TypeScript, React via Vite, TanStack Router, TanStack Query, TanStack Forms, Zod,
Zustand, axios, Tailwind CSS with shadcn/ui, Chart.js for dashboard visualizations.

Additional constraints:

- **Configuration**: Every configurable value — database URL, JWT secret, API keys, CORS origins,
  feature toggles — MUST be read from environment variables through a `pydantic-settings` settings
  class injected via `Depends`. Secrets MUST NOT be hard-coded or committed, and a `.env.example`
  listing every required key MUST be kept current.
- **Charts**: Dashboard visualizations MUST use Chart.js behind a typed `shared/ui` wrapper
  component; chart datasets MUST be derived from TanStack Query data, never from a Zustand store.
- **Design tokens**: Styling MUST use the tokens in `Task/designs/DESIGN_TOKENS.md` through Tailwind
  configuration and CSS custom properties. Ad-hoc hex colors, font sizes, and spacing values in
  components are forbidden.
- **Migrations**: Schema changes MUST ship as versioned migrations reviewed alongside the code that
  requires them. Editing a database by hand is not a schema change.

## Development Workflow & Quality Gates

1. Every feature starts from an epic in `Task/Epics/` and proceeds through `/speckit-specify`,
   `/speckit-plan`, `/speckit-tasks`, then `/speckit-implement`.
2. A change is mergeable only when all gates pass:
   - Backend: strict type checking clean; no raw SQL; no sync DB calls; layer boundaries respected.
   - Frontend: `tsc --noEmit` clean with zero `any`; lint clean; FSD import direction respected.
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

**Version**: 1.0.0 | **Ratified**: 2026-08-19 | **Last Amended**: 2026-08-19
