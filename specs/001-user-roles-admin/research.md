# Phase 0 Research: User Roles, Authorization & Super Admin User Management

**Feature**: `001-user-roles-admin` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)

**Purpose**: Resolve the two outstanding `[NEEDS CLARIFICATION]` markers from the specification and
settle every technology decision the plan depends on, so that `plan.md` and `data-model.md` contain
no unknowns.

**Note on sources**: The project's global guidance prefers Context7 MCP for library documentation.
No Context7 server is connected to this session, so version-sensitive facts below were verified by
web search instead, and the sources are cited at the end. Decisions that rest on general
architectural reasoning rather than library specifics are marked as such.

---

## Part A — Resolving the specification's open questions

### R-01: Trainer invitation mechanism (resolves FR-025)

**Decision**: The invitation email carries a **single-use setup link that expires 24 hours after
issue, and no password**. The Super Admin never sees or handles a credential. A Super Admin can
re-issue the invitation, which invalidates any earlier outstanding link for that account.

**Rationale**: US-01.01 offers "temporary password OR invite email with setup link" as alternatives,
so one had to be chosen. A setup link is the stronger option on every axis that matters here:

- No working credential ever rests in an inbox or in a Super Admin's notes. A temporary password is
  a live credential from the moment it is generated until it is changed, and email is not a
  confidential channel.
- Expiry and single-use consumption are natural properties of a link and awkward ones for a
  password. US-01.01's own requirement that the password "must be changed on first login" is an
  attempt to bolt link semantics onto a password; using a link gets it for free.
- The failure mode is benign and self-service: an expired link produces "request a new one" rather
  than a support call about a password that no longer works.

**Alternatives considered**:

| Alternative | Rejected because |
|---|---|
| Temporary password only | Leaves a live credential in email indefinitely; forced-change-on-first-login is a partial mitigation that still leaves the window open, and it needs its own state flag and interception logic. |
| Both link and temporary password in one email | Widest exposure window plus two first-sign-in paths to build, test, and support. No benefit the link alone does not provide. |
| Link primary, temporary password as an admin-triggered fallback | Reasonable, but it is the temporary-password design with extra branching. If phone-based onboarding support turns out to be needed, re-issuing the link (FR-028) already covers it. |

**Consequence for the design**: an account exists in a real state where it has no usable password.
The data model represents this as a nullable password hash rather than a separate "pending" status,
because the account genuinely is Active — it simply cannot be signed into yet. See
[data-model.md](./data-model.md) §2.

---

### R-02: Roles a Super Admin may assign at creation (resolves FR-030)

**Decision**: A Super Admin may create an account in **any of the four roles**. Every created
account follows the same invitation-driven first-password flow regardless of role.

**Rationale**: US-01.01's own acceptance criteria describe the interaction as *"From Users tool,
click 'Create User' → Select 'Trainer' role"*. That is a generic create-user form with a role
selector, and Trainer is the role the story happens to walk through — not evidence that the selector
holds a single option. Three further considerations point the same way:

- US-01.11, US-01.12, and US-01.13 are specified across all four roles. Without a way to bring Coach
  and Player/Parent accounts into existence, those stories can only be proven against database
  fixtures, not demonstrated in the running application.
- Epic-01 places the Users tool in scope as a *global* user directory with "Edit user accounts and
  profiles" as a Super Admin capability, and describes the Super Admin as able to "override any
  rule". A directory that lists four roles but can only create one is an odd artifact.
- Epic-01's actual constraint is *"ONLY Super Admin can create trainer accounts (no
  self-registration)"*. That restricts who may create trainers; it says nothing limiting what else a
  Super Admin may create.

**Alternatives considered**:

| Alternative | Rejected because |
|---|---|
| Trainer only, other roles seeded as test fixtures | Truest to a narrow reading of US-01.01, but makes three of the five user stories undemonstrable outside the test suite, and the seeded accounts would need building anyway — as fixtures rather than as a feature. |
| Trainer and Coach only | Splits the difference without a principled line. Player/Parent profile editing is explicitly in US-01.11, so it needs real accounts too. |

**Boundary this decision does not cross**: admin-created Coach and Player/Parent accounts do **not**
carry the relationships those roles will eventually need — a Coach's single-trainer assignment and a
player's trainer associations remain out of scope, exactly as the spec's Out of Scope section states.
Such an account exists, signs in, and edits its own profile; it belongs to no organization yet. When
the ShareLink flows arrive, they add a second path to account creation rather than replacing this
one.

---

## Part B — Technology decisions

The constitution fixes the stack, so the research below settles *how* to use each locked component,
not which to choose.

### R-03: Session mechanism — opaque server-side session, not stateless JWT

**Decision**: Sessions are **opaque random tokens persisted server-side**, delivered in an
`HttpOnly; Secure; SameSite=Lax` cookie. The stored record holds issue time, last-activity time, and
expiry; a sliding 7-day inactivity window is enforced by updating last-activity on use.

**Rationale**: FR-012 requires that every existing session for an account is invalidated *the moment*
its status leaves Active, and SC-007 puts a one-minute ceiling on that. A self-contained JWT cannot
be withdrawn before its own expiry without a server-side revocation list — at which point every
request consults the database anyway and the statelessness that motivated the JWT is gone. A session
table delivers immediate revocation directly: deactivation and erasure delete the account's session
rows in the same transaction as the status change.

Storing the token in an `HttpOnly` cookie rather than in JavaScript-reachable storage keeps it out of
reach of cross-site scripting. `SameSite=Lax` is sufficient because the frontend is served from the
same site; the API accepts no cross-site state-changing requests.

The constitution names "JWT secrets" when listing values that must come from environment variables.
That is an example of configuration hygiene, not a mandate to use JWTs, so this decision does not
conflict with it.

**Alternatives considered**:

| Alternative | Rejected because |
|---|---|
| Stateless JWT access token | Cannot satisfy FR-012's immediate revocation without a database-backed denylist, which reintroduces the per-request lookup while adding token-parsing complexity. |
| Short-lived JWT plus refresh token | Bounds the revocation gap to the access-token lifetime instead of closing it, and doubles the credential surface. Justified at multi-service scale; this is one service. |
| Token in `localStorage` with an `Authorization` header | Readable by any injected script. No benefit over a cookie for a same-site frontend. |

### R-04: Password hashing — Argon2id via `pwdlib`

**Decision**: Hash with **Argon2id through `pwdlib[argon2]`**.

**Rationale**: Argon2id is the current recommendation for password storage, and `pwdlib` is the
actively maintained helper the FastAPI documentation itself now uses. The long-standing alternative,
`passlib`, is effectively unmaintained and depends on the standard-library `crypt` module, which PEP
594 removed in Python 3.13 — a dependency that is already a liability. `pwdlib` also supports
verifying a legacy hash and transparently upgrading it, which costs nothing now and matters if hashes
are ever imported.

**Alternatives considered**: `passlib[bcrypt]` — rejected on maintenance and the `crypt` removal.
Calling `argon2-cffi` directly — workable, but `pwdlib` supplies the hash-identification and upgrade
handling that would otherwise be hand-written.

### R-05: Password strength check — length plus a bundled breached-password list

**Decision**: Enforce a 12-character minimum and reject any password appearing in a **bundled list of
the most common breached passwords**, checked in-process.

**Rationale**: FR-014 requires a breached-password check. Doing it against a remote service such as
Have I Been Pwned's range API would introduce a network call on the password-setting path, meaning a
third-party outage blocks onboarding and every test needs the call stubbed. A bundled list is
deterministic, offline, and adds a single file to the repository. It catches the passwords that
actually appear in credential-stuffing attacks, which is the threat FR-014 targets.

**Alternatives considered**: the HIBP k-anonymity range API — deferred, not rejected; it can be added
later as an optional second check behind an environment flag without changing the validation
interface. Composition rules such as mandatory symbol classes — rejected as they push users toward
predictable substitutions without measurably improving strength.

### R-06: Sign-in rate limiting — durable attempt records, not in-memory counters

**Decision**: Record failed sign-in attempts in the database, keyed by **email address and by client
origin**. Refuse further attempts once 10 failures accumulate within 15 minutes; allow attempts
again automatically as the window slides past them.

**Rationale**: SC-011 sets exactly these numbers and requires legitimate access to resume
automatically, which rules out an administrative unlock. Persisting attempts rather than holding them
in process memory means a restart cannot clear an attacker's counter, and the records double as
security-event evidence. Keying on both email and origin blocks credential-stuffing against one
account and spraying across many from one source.

**Alternatives considered**: an in-process sliding window — simpler and adequate for one process, but
loses state on restart, which is precisely when an attacker benefits. A fixed lockout requiring
administrator intervention — contradicts SC-011's automatic recovery.

### R-07: Profile photos — local filesystem with a generated thumbnail

**Decision**: Store originals and a generated 128×128 thumbnail on the **local filesystem** under a
configured upload directory, named by an unguessable key. Accept JPEG, PNG, and WebP up to 5 MB.
Validate the actual decoded image rather than trusting the declared content type or file extension.
Serve through an application route that checks the requester's session. Delete the previous original
and thumbnail when a photo is replaced.

**Rationale**: The epic names "file storage" as an external dependency without choosing one, and this
feature runs against SQLite on a single host, so a local directory matches the deployment. An
application-served route rather than a static mount lets the authorization rule stay in one place and
keeps the storage layout private. Validating by decoding closes the path where a renamed executable
or a malformed image reaches an image library. Deleting replaced files satisfies the spec's edge case
on photo replacement.

**Alternatives considered**: object storage such as S3 — correct at multi-host scale and worth
adopting when the deployment demands it; the storage interface is defined as a port so the swap is
local. Storing image bytes in SQLite — bloats the database file and the backups, and forfeits
streaming responses.

### R-08: Privacy erasure — in-place anonymization plus a separate compliance record

**Decision**: Erasure **updates the existing account row in place** — name to "Deleted User", email
to `deleted_{account_id}@example.com`, phone and other identifiers cleared, photo discarded, status
to Deleted — and writes a row to a separate compliance table holding the original identifier,
original email, acting Super Admin, reason, and timestamp. Every other table's reference to the
account is left untouched.

**Rationale**: FR-046 and FR-047 require history and reporting totals to survive an erasure exactly,
which rules out deleting the row: foreign keys from attendance, payments, and rosters must continue
to resolve, and a row that still exists is what makes them resolve. Anonymizing in place means
downstream epics need no special handling — they join to a user and read "Deleted User", with no
awareness that erasure exists. Keeping the compliance record in its own table, readable only by Super
Admins, means the retained original email is not reachable from any ordinary account view, which is
what FR-049 asks for.

The placeholder address is derived from the account identifier so it is unique without a lookup, and
`example.com` is reserved by RFC 2606 and can never receive mail.

**Alternatives considered**: hard deletion with history rewritten to a shared "deleted" sentinel
account — destroys per-person history and would corrupt any per-participant reporting. Encrypting
personal fields and discarding the key ("crypto-shredding") — stronger against database backups, but
it requires per-account key management across every table before any of it is needed, and it leaves
ciphertext that still reads as personal data to a strict auditor.

**Flagged for legal review**: retaining the original email address is Epic-01's stated requirement
and is implemented, but it sits in tension with a strict reading of an erasure request. The spec's
Assumptions section already records this; it needs the operator's legal basis confirmed before
launch, not a technical fix.

### R-09: Guarding the last Super Admin

**Decision**: Before any deactivation or erasure, count the remaining Active Super Admins **inside
the same transaction** as the status change, and refuse when the target is the last one. Separately,
refuse any Super Admin's attempt to deactivate or erase their own account.

**Rationale**: FR-041 requires both guards. A check performed outside the transaction can be
overtaken by a concurrent second deactivation, leaving the platform with no administrator — the exact
outcome the rule exists to prevent. SQLite serializes write transactions, so a count-then-write
inside one transaction is sufficient here without additional locking; the same code needs an explicit
row lock if the store is ever changed to one with concurrent writers, and the repository is
commented to that effect.

### R-10: Concurrent status changes

**Decision**: Carry a **version counter on the account row** and require the caller's observed
version to match on any status change, rejecting a stale write with a conflict response.

**Rationale**: The spec's edge case requires that when two Super Admins act on one account at the
same time, one action wins and the other is told the account changed underneath it. A version check
produces exactly that, and it lets the interface re-fetch and show the current state instead of
silently discarding an administrator's intent.

### R-11: Email delivery — a port with an SMTP implementation and a development sink

**Decision**: Define an email-sending **interface** and provide two implementations selected by
environment: SMTP over `aiosmtplib` for real delivery, and a local sink that writes messages to disk
for development and tests. Send within the request, and surface a send failure to the Super Admin so
they can re-issue the invitation.

**Rationale**: The invitation is the only email this feature sends, so a background queue and an
outbox table would be infrastructure with one caller. Reporting the failure to the Super Admin, who
can act immediately via the existing re-invite capability (FR-028), matches the spec's assumption
that non-delivery is visible to them. A local sink keeps tests and development free of a mail server.

**Alternatives considered**: a transactional email API such as SendGrid or Postmark — likely correct
for production deliverability and reachable through the same interface without touching callers. A
persisted outbox with a retry worker — the right answer once more than one email matters; premature
for a single invitation.

### R-12: SQLite in async mode

**Decision**: Connect through **`aiosqlite`** with SQLAlchemy's async engine. On every new
connection, enable `foreign_keys` and set `journal_mode=WAL` and a busy timeout. Keep one
`AsyncSession` per request, supplied by dependency injection, committing at the end of a successful
request and rolling back on failure.

**Rationale**: SQLite does not enforce foreign keys unless asked per connection, and this design
depends on those keys to hold history to accounts. WAL mode lets reads proceed during a write, which
matters because the user directory is read-heavy while administrative actions write. A busy timeout
converts brief write contention into a short wait rather than an immediate error.

**Known limitation worth stating plainly**: SQLite permits one writer at a time. That is
comfortable for this feature's write volume — administrative actions and profile saves — and the
repository boundary the constitution mandates is what will make a later move to PostgreSQL a
configuration and migration exercise rather than a rewrite.

**Constitutional exception**: `PRAGMA` statements cannot be expressed as ORM or Core constructs and
must be issued as literal SQL on connection setup. This is recorded as a justified deviation in
`plan.md` §Complexity Tracking. It is confined to one engine-configuration function, is parameterless,
and touches no user input.

### R-13: Schema migrations — Alembic

**Decision**: Manage schema with **Alembic**, in async mode, one revision per schema change,
reviewed alongside the code that needs it. Never create tables from model metadata outside tests.

**Rationale**: The constitution requires versioned migrations and forbids hand-editing a database.
Alembic is the SQLAlchemy-native tool and autogenerates a starting revision from the models.
SQLite's limited `ALTER TABLE` support means some later changes need Alembic's batch mode; that is a
known cost of the locked storage choice, not a surprise.

### R-14: Authorization enforcement — dependency for the role gate, service for the rest

**Decision**: Enforce **role membership in a FastAPI dependency** applied to each route, and enforce
every rule that depends on the target's state — self-only profile access, last-Super-Admin, no
self-deactivation, no editing a Deleted account — **in the service layer**. No permission decision
lives in the frontend alone.

**Rationale**: FR-015 requires enforcement on request receipt regardless of interface. Splitting the
check this way puts each rule where its information lives: the role gate needs only the session, so a
dependency rejects unauthorized callers before any work begins, while the state-dependent rules need
the loaded target and belong with the business logic per the constitution's layering principle. The
frontend hides controls the role cannot use, but that is presentation, never protection.

### R-15: Role-specific profile data — separate tables, not a JSON column

**Decision**: One common profile table for every account, plus **four optional one-to-one detail
tables** — trainer organization, coach professional detail, player detail, parent contact — each
present only for the matching role.

**Rationale**: The constitution forbids `any` on the frontend and requires strict typing throughout;
a JSON blob of role-specific fields defeats both, pushing validation to runtime and typing to
`unknown` at every read. Separate tables give each field a real column with real constraints, let
Pydantic model each role's profile precisely as a discriminated union, and give later epics somewhere
to add their own columns — trainer billing identifiers in Epic-05, coach-trainer assignment in
Epic-01's later slice — without touching the accounts table.

**Alternatives considered**: a single wide profile table with nullable columns for every role —
readable at four roles, but every column becomes nullable and nothing prevents a Coach row carrying a
jersey number. A JSON detail column — flexible, and wrong for a schema this well understood.

### R-16: Append-only audit trail

**Decision**: Expose **only insert and select** on the audit repository — no update or delete method
exists — and add a SQLite trigger that raises on `UPDATE` or `DELETE` against the audit table.

**Rationale**: FR-055 requires that no one can alter or remove an audit entry through the platform.
An interface with no mutation method makes the application incapable of it; the trigger closes the
path where a future migration or an incautious script bypasses the repository. The trigger is DDL in
an Alembic revision, so it is versioned like everything else.

### R-17: Frontend structure under Feature-Sliced Design

**Decision**: Map this feature onto the FSD layers as follows.

| Layer | Contents for this feature |
|---|---|
| `app` | Application entry, router registration, TanStack Query client, global providers, Tailwind entry stylesheet |
| `pages` | Sign-in, set-password, my-profile, admin user directory, admin user detail |
| `widgets` | User directory table with its paging and filter bar, profile form shell |
| `features` | `auth/sign-in`, `auth/set-password`, `profile/edit-own`, `admin/create-user`, `admin/deactivate-user`, `admin/reactivate-user`, `admin/erase-user` |
| `entities` | `user` — the account and profile models, query hooks, and query-key factory; `session` — the current-user query and role predicates |
| `shared` | `api` (the single axios instance and its interceptors), `ui` (all shadcn/ui primitives), `lib`, `config` |

The `processes` layer is **not created**. FSD treats it as optional and increasingly discouraged, and
this feature has no cross-page flow that needs it; the set-password journey is a single page reached
by link. A later slice that needs one — multi-step registration, for instance — adds the layer then.
This is a deliberate documented choice, not an oversight.

**Rationale**: The constitution requires the layer order and one-way imports. Putting the query hooks
in `entities/user` rather than in each feature means the directory, the profile page, and the
administrative actions share one query-key factory, so a mutation invalidates every view of the same
data. Zustand holds no server data here at all; the only global client state this feature needs is
transient interface state, which is why the store is small.

### R-18: Frontend build and component setup — Tailwind CSS v4, shadcn/ui via the Vite path

**Decision**: Tailwind CSS **v4** through the `@tailwindcss/vite` plugin, configured in CSS rather
than a JavaScript config file, with shadcn/ui installed by its Vite instructions and `tw-animate-css`
for animation. Design tokens from `Task/designs/DESIGN_TOKENS.md` are declared as CSS custom
properties in the Tailwind entry stylesheet and exposed as theme values.

**Rationale**: Tailwind v4 is the current major version and is what shadcn/ui's Vite instructions now
target; v4 replaced the three-import preamble and the JavaScript config with a CSS-first setup, and
new shadcn/ui projects get `tw-animate-css` in place of `tailwindcss-animate`. Declaring the epic's
tokens as custom properties satisfies the constitution's ban on ad-hoc colors and sizes while keeping
the trainer-branding override mechanism a later epic needs straightforward.

### R-19: Forms and typed routing

**Decision**: **TanStack Form v1** (`@tanstack/react-form`, 1.33.x at time of writing) with Zod
schemas as the validation adapter, and **TanStack Router** with file-based routing, generated route
tree, and Zod-validated search parameters for the directory's paging and filter state.

**Rationale**: The constitution mandates both libraries with schema validation matching backend
constraints. Defining each form's Zod schema once and deriving the TypeScript type from it keeps a
single source of truth per form, and the same schema shape mirrors the Pydantic model on the other
side of the boundary. Putting the directory's page, search term, role filter, and status filter in
Zod-validated search parameters makes that state shareable by URL and typed at every read, which is
what the constitution's routing rule asks for.

### R-20: Testing approach

**Decision**:

| Level | Tooling | What it proves |
|---|---|---|
| Backend unit | pytest, `pytest-asyncio` | Service rules in isolation with a fake repository: status transitions, last-Super-Admin guard, password policy, anonymization mapping |
| Backend integration | pytest with `httpx` `ASGITransport` against a temporary SQLite file | Each endpoint end to end, including the permission matrix and the audit rows written |
| Contract | pytest asserting the generated OpenAPI document against `contracts/openapi.yaml` | The implementation has not drifted from the published contract |
| Frontend unit | Vitest, React Testing Library, MSW | Form validation, permission-driven rendering, query-key invalidation |

**Rationale**: The permission matrix in FR-016 to FR-020 and SC-002 is the highest-risk area, and it
is only meaningfully testable at the integration level where a real request carries a real session —
a unit test of a dependency proves the dependency, not the route. A temporary SQLite file per test
session, migrated with Alembic, means the tests exercise the same schema production gets. MSW lets
frontend tests assert against the same contract rather than against hand-stubbed functions.

---

## Consolidated decisions

| ID | Area | Decision |
|----|------|----------|
| R-01 | Invitation | Single-use setup link, 24-hour expiry, no password in email |
| R-02 | Role assignment | Super Admin may create any of the four roles |
| R-03 | Session | Opaque server-side token, `HttpOnly` cookie, sliding 7-day inactivity |
| R-04 | Hashing | Argon2id via `pwdlib` |
| R-05 | Password policy | 12-character minimum plus bundled breached-password list |
| R-06 | Rate limiting | Durable attempt records; 10 failures per 15 minutes, sliding |
| R-07 | Photos | Local filesystem, generated thumbnail, decode-validated, app-served |
| R-08 | Erasure | In-place anonymization plus Super-Admin-only compliance record |
| R-09 | Last admin | Transactional count guard, plus no self-deactivation |
| R-10 | Concurrency | Version counter on the account row, conflict on stale write |
| R-11 | Email | Sender interface; SMTP implementation and a development sink |
| R-12 | Storage | `aiosqlite`, foreign keys on, WAL, one session per request |
| R-13 | Migrations | Alembic, async, one revision per change |
| R-14 | Authorization | Role gate in a dependency, state-dependent rules in services |
| R-15 | Profiles | Common table plus four one-to-one role detail tables |
| R-16 | Audit | Insert and select only, enforced additionally by a trigger |
| R-17 | Frontend layers | FSD as tabulated; `processes` deliberately not created |
| R-18 | Styling | Tailwind CSS v4 via Vite plugin, shadcn/ui, tokens as CSS properties |
| R-19 | Forms and routing | TanStack Form v1 with Zod; Zod-validated search parameters |
| R-20 | Testing | pytest and httpx for backend, Vitest with MSW for frontend |

**No `[NEEDS CLARIFICATION]` markers remain.** R-01 and R-02 have been written back into the
specification at FR-025 and FR-030.

---

## Sources

Version-sensitive claims above were checked against:

- [Tailwind v4 — shadcn/ui](https://ui.shadcn.com/docs/tailwind-v4)
- [Vite installation — shadcn/ui](https://ui.shadcn.com/docs/installation/vite)
- [Announcing TanStack Form v1 — TanStack Blog](https://tanstack.com/blog/announcing-tanstack-form-v1)
- [`@tanstack/react-form` — npm](https://www.npmjs.com/package/@tanstack/react-form)
- [Search Params — TanStack Router Docs](https://tanstack.com/router/latest/docs/guide/search-params)
- [OAuth2 with Password (and hashing) — FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Password hash — FastAPI Users](https://fastapi-users.github.io/fastapi-users/latest/configuration/password-hash/)
- [Introducing pwdlib — François Voron](https://www.fvoron.com/blog/introducing-pwdlib-a-modern-password-hash-helper-for-python/)
- [passlib maintenance discussion — fastapi/fastapi #11773](https://github.com/fastapi/fastapi/discussions/11773)

Architectural decisions R-03, R-08, R-09, R-10, R-14, R-15, and R-16 follow from the specification's
own requirements rather than from external documentation, and are argued from those requirements
above.
