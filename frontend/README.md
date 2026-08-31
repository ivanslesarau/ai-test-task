# PracticePerfect Web

React (Vite) + TypeScript frontend implementing Epic-01 in full, across two features:

- `001-user-roles-admin` — user roles, authorization, Super Admin management, ShareLink onboarding,
  multi-trainer association, portal branding, and parent/child family accounts.
- `002-coach-availability-impersonation` — coach invitations, weekly availability ("My Times") for
  coaches and player profiles, and Super Admin impersonation.

See each feature's own `contracts/frontend-contracts.md` for the routes, query keys, and Zod schemas
that feature's slice implements — `../specs/001-user-roles-admin/contracts/frontend-contracts.md` and
`../specs/002-coach-availability-impersonation/contracts/frontend-contracts.md`.

## Setup

Requires Node.js 22 LTS+.

```bash
cd frontend
npm install
cp .env.example .env    # VITE_API_BASE_URL — defaults to /api/v1 via the dev proxy
npm run dev             # http://localhost:5173
```

The dev server proxies `/api` to the backend (see `vite.config.ts`) so the session cookie stays
first-party — the backend must be running per `../backend/README.md`.

## Environment variables

| Variable | Notes |
|---|---|
| `VITE_API_BASE_URL` | Base path for the centralized axios client in `src/shared/api/` |

## Architecture

Strict Feature-Sliced Design (constitution Principle IV). Layers, outermost to innermost, and the
one-directional import rule enforced by `eslint-plugin-boundaries` (`eslint.config.js`) — a layer may
only import from itself or a layer further down this list:

```
app → pages → widgets → features → entities → shared
```

- **`shared/`** — cross-cutting, no feature knowledge. `shared/ui/` holds every shadcn/ui and
  generic Tailwind component; `shared/api/` holds the single axios instance, interceptors, and
  hand-mirrored OpenAPI response types. No UI component outside `shared/ui/` renders raw
  shadcn/Tailwind primitives directly, and no code outside `shared/api/` imports `axios`.
- **`entities/`** — business objects (`user`, `session`) and their TanStack Query hooks/query keys.
- **`features/`** — one user-facing action each (sign in, create user, deactivate user, edit own
  profile, ...), each owning its form, validation schema, and mutation hook.
- **`widgets/`** — compositions of entities/features into a self-contained page section (the user
  directory table, the profile form shell).
- **`pages/`** — route-level assembly of widgets; no business logic of its own.
- **`app/`** — providers, the Zustand UI store, global styles, router setup.

Two typed state systems, never mixed:

- **TanStack Query** owns all server state — every fetch/mutation of API data goes through a query
  hook in `entities/*/api/` or `features/*/model/`. Never store API response data in Zustand.
- **Zustand** (`app/store/ui-store.ts`) owns only global client UI state (sidebar collapsed, theme,
  which confirmation dialog is pending). The pending-action store holds an id, never a fetched
  object — the owning feature re-fetches or reads it fresh from the query cache.

Forms use TanStack Form with Zod validators mirroring the backend's Pydantic schemas
(`features/*/model/schema.ts`). Routing uses TanStack Router's file-based, fully-typed routes
(`src/routes/`) with Zod-validated search params.

No `any` anywhere — `@typescript-eslint/no-explicit-any` is an ESLint error. Where a value is
genuinely dynamic, use `unknown` and a type guard or a narrowing cast with a comment explaining why
it's safe (see `entities/user/api/use-own-profile.ts` and its `field-values.ts` helper for an
example: which fields exist is only known at runtime, from the server's `editable_fields` list).

## Extension (2026-08-26): the `ctx` query-key namespace and branding

Two conventions a contributor extending player-onboarding, multi-trainer, or branding work must
follow, argued in `../specs/001-user-roles-admin/research.md` R-26 and R-27:

- **Every query for data scoped to one trainer is keyed `['ctx', trainerId, ...]`** —
  `entities/trainer-context/api/query-keys.ts`. This is the standing convention Epics 02-08 inherit;
  a query for trainer-scoped data that doesn't begin with this namespace is a bug, not a style
  choice. Switching context (`useSwitchTrainerContext`) removes the whole `['ctx']` subtree from the
  cache *before* the session refetch resolves — reordering that is what would let one frame render
  the previous trainer's data (FR-087).
- **A logo renders through `<img>` only.** Never `<object>`, `<embed>`, or
  `dangerouslySetInnerHTML` — an SVG loaded any other way can execute script in the viewer's
  browser. `shared/lib/brand-palette.ts` derives the CSS custom properties
  (`--brand-primary`/`-soft`/`-deep`/`-rgb`, matching `Task/designs/DESIGN_TOKENS.md`, plus a
  WCAG-safe `--brand-surface`/`--brand-on-surface` pair the design tokens don't name) that
  `widgets/branding-provider/` sets at `routes/_authed.tsx` and `routes/join.$code.tsx` — never at
  `routes/__root.tsx`, which also carries `/login` and `/set-password`. A CI check greps for
  `<object|<embed|dangerouslySetInnerHTML` near any file mentioning "branding" and fails the build if
  one is found.

## Extension (2026-08-28): coach invitations, availability, impersonation (feature 002)

Three roles gain new reachable pages, argued in full in
`../specs/002-coach-availability-impersonation/contracts/frontend-contracts.md`:

- **Coach** — `/my-times` (their own stated week; the primary nav's `coach` case is no longer empty).
- **Trainer** — `/trainer/coaches` (roster and invitations) and `/trainer/coaches/$coachUserId` (one
  coach's full week, read-only, reached only as a roster-row action — not a nav entry, exactly like
  `/admin/users/$userId`).
- **Player/Parent** — `/availability`, shown to both the parent shape and the signed-in-child shape of
  that role (unlike Approvals/Requests, which the child shape does not see).
- **Super Admin** — `/admin/impersonations` (the append-only history).

Conventions a contributor extending this slice must follow:

- **One summary formatter.** `entities/availability/model/format-summary.ts` is the only place a day
  name, a 12-hour clock, or the en-dash between a range's start and end is computed. The API always
  returns structured `{day_of_week, start_minute, end_minute}` slots, never a pre-baked string — a
  roster row's "Best times" cell and the full-week view read the same function, so they can never
  disagree (research.md R2-12).
- **`queryClient.clear()` on both impersonation boundaries.** Starting and ending an impersonation are
  the only two places in the app permitted to clear the whole query cache — every cached response
  belongs to the identity active before the switch, and leaving it in place would let a Super Admin's
  directory page (or the impersonated person's own data) survive into the wrong portal
  (`entities/impersonation/api/use-start-impersonation.ts`, `use-end-impersonation.ts`).
- **Nothing about impersonation is inferred client-side.** The banner
  (`widgets/impersonation-banner/`) renders purely from `session.impersonation` being non-null; its
  countdown is decorative, and only the server, on the next request, actually ends an impersonation.
  A session describing a Trainer is turned away from `/admin/users` by the same route guard that
  turns away any Trainer — no impersonation-specific branching exists in any guard.

## Quality gates

```bash
npm run lint        # ESLint — no-explicit-any and the FSD import-boundaries rule
npm run typecheck    # tsc -b --noEmit, strict
npm run test          # Vitest + React Testing Library + MSW
npm run build         # tsc -b && vite build
```
