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

---

# Phase 0 Research — Extension: ShareLink Onboarding, Multi-Trainer & Portal Branding

**Date**: 2026-08-26 | **Covers**: spec FR-065 – FR-104, SC-015 – SC-025, User Stories 6–8

**Note on sources**: Context7 MCP is connected in this session, unlike the original Phase 0 run.
R-27's claims about Python's XML parsers were checked against the CPython documentation through it
and are cited at the end. The remaining decisions follow from the specification and from the
architecture already built, and are argued from those.

## Part C — Decisions for the extension

### R-21: ShareLink codes are stored in clear, unlike every other token in this system

**Decision**: `share_links.code` holds the URL-safe code **as issued**, indexed and unique. It is
generated with `secrets.token_urlsafe(16)` — 128 bits of entropy in 22 characters.

**Rationale**: Sessions (R-03) and setup invitations (R-01) store only a SHA-256 of their secret,
because those secrets are shown once and a database leak must not yield a usable credential. A
standing player ShareLink is the opposite kind of object: FR-069 requires the trainer to be able to
**see and copy it again at any time**, and a hash cannot be un-hashed to satisfy that. The link is
also designed to be published — printed on a flyer, posted publicly — so its confidentiality is not
a security property at all. What it grants is exactly one thing: the right to become a player of one
trainer, which the trainer is offering to the public anyway.

128 bits is nonetheless the entropy floor, because FR-066 forbids codes that can be found by trying
values and FR-070 must not become a trainer-enumeration oracle. Combined with the per-origin
throttle in R-30, SC-021's 10,000-attempt trial cannot succeed.

**Alternatives rejected**:

- *Hash the code like the others.* Then `GET /me/share-link` cannot render the link, and the trainer
  would have to regenerate — and reprint — every time they lost the copy. That defeats the purpose
  of a standing link.
- *Store a hash and keep a decryptable copy.* A reversible encryption key sitting beside the data it
  protects is theatre; it adds a key to manage and changes nothing an attacker faces.
- *Short human-friendly codes (`ABC123`, as the epic's example URL shows).* Six alphanumerics is
  ~31 bits, which a throttle alone cannot defend for a link that never expires. The epic's URL is
  illustrative; the requirement it must satisfy is FR-066.

### R-22: One standing link per trainer, created with the account

**Decision**: A `share_links` row of kind `player_standing` is created **in the same transaction as
the trainer account**, and a data migration backfills one for every trainer that already exists.
`GET /me/share-link` is therefore a pure read. Regenerating deactivates the current row
(`is_active = false`, `revoked_at` set) and inserts a new one; old rows are never deleted, because
`trainer_player_associations.share_link_id` points at them and FR-069 requires those associations to
survive.

**Rationale**: The obvious alternative — create the link lazily on first read — turns a `GET` into a
write, which means an idempotent-looking endpoint takes the SQLite write lock and can conflict with
an administrative action already holding it (plan.md §Technical Context). Creating it eagerly costs
one row per trainer and removes the whole class of problem. The spec's assumption fixes the count at
one standing link per trainer, so there is no collection to manage.

**Alternatives rejected**: lazy creation (above); many named links per trainer (that is campaign
tracking, which the spec defers to Epic-06).

### R-23: Joining is one transaction, and there are three ways in

**Decision**: Three operations, each atomic:

| Operation | Caller | Effect |
|---|---|---|
| `GET /join/{code}` | anyone | Read-only preview: trainer business name and branding, or a flat refusal |
| `POST /join/{code}/register` | no session | Account + profile + player detail + parent contact + association + session, in **one** transaction |
| `POST /join/{code}/accept` | signed-in `player_parent` | Association only, plus a context switch |

FR-083 requires that a failed registration leave nothing behind, which a single
`async with session.begin()` in `join_service` gives for free. The alternative — reusing
`user_admin_service.create_user` and then associating in a second call — would leave an orphaned
account whenever the second call failed, and would also have to suppress the invitation email that
path sends.

**On the duplicate-email race** (spec edge case): the transaction relies on the existing unique index
on `users.email`, catching `IntegrityError` in the service and translating it to the same
`email_taken` domain error the admin path already raises. Checking first and inserting second is a
race by construction; the index is the only thing that is actually atomic.

### R-24: The active trainer context lives on the player's row, not in the session

**Decision**: `player_details.active_trainer_user_id`, nullable, FK → `users.id`.

**Rationale**: FR-086 requires the last-used trainer to be restored **at sign-in, on any device**.
That rules out anything session-scoped (a new sign-in creates a new session row, so the value would
reset) and anything browser-scoped (`localStorage` is per-device, and the spec's assumption states
the value is remembered against the account). A column on the player's own detail row is the
narrowest place that satisfies both: it is already one-to-one with the account, it is only
meaningful for `player_parent` accounts, and it costs no join on the session read that needs it.

The column is nullable because a player may legitimately hold zero associations — a Super
Admin-created account (FR-030) or one whose only trainer was deactivated (FR-089). Reading it always
goes through one service function that repairs a dangling or stale value rather than trusting it:
if the referenced association is missing, inactive, or its trainer is not Active, the service picks
another Active association and writes the correction back.

**Alternatives rejected**: a column on `sessions` (dies with the session); `localStorage`
(per-device, and the server could not enforce it); a `last_used_at` column on the association row,
picking the maximum (it makes "which context am I in" a query with a tie-break rather than a fact,
and switching context becomes an update whose meaning depends on clock ordering).

### R-25: Context is resolved server-side; the client never names a trainer

**Decision**: No endpoint takes a `trainer_id` parameter to select context. Context-scoped reads
resolve the trainer from `active_trainer_user_id` for the calling account. Switching is one
operation, `PUT /me/trainer-context`, whose body names the trainer to switch to and which validates
that the caller holds an Active association with it.

**Rationale**: FR-087 makes context a **data-isolation boundary**, not a display preference, and
FR-090 makes leakage across it a confidentiality failure. If the trainer came in as a request
parameter, every endpoint that Epics 02–08 add would have to remember to validate that the caller is
associated with the trainer it names — and one forgotten check is a cross-tenant read. Resolving
context from the caller's own row means an endpoint that forgets is not vulnerable, merely wrong,
and the check lives in one dependency (`get_trainer_context`) exactly as R-14 puts the role gate in
one dependency.

The cost is that context is server state, so the client must invalidate cached data when it changes;
R-26 handles that.

**Alternatives rejected**: `?trainer_id=` per endpoint (above); an `X-Trainer-Context` header (same
validation burden, plus it is invisible in a URL, so a bug reproduces only with the header attached,
and TanStack Query would have to carry it in the key anyway).

### R-26: Context-scoped query keys are namespaced, and switching drops that namespace

**Decision**: Every TanStack Query key for data that belongs to one trainer is namespaced
`['ctx', trainerId, ...]`. Switching context calls the mutation, awaits it, then
`queryClient.removeQueries({ queryKey: ['ctx'] })` and refetches the session.

**Rationale**: Namespacing is what makes scenario 4 of User Story 7 — "nothing belonging to Trainer A
remains on screen" — structurally true rather than a thing to remember: a component asking for
context data under the new trainer's namespace cannot be handed the old trainer's cached response,
because that response is filed under a different key. The `removeQueries` call is then a
memory concern and a belt-and-braces guarantee, not the mechanism.

This feature has almost nothing context-scoped yet — the trainer's branding and the roster are the
only entries — which is precisely why the convention is fixed **now**, in
`contracts/frontend-contracts.md` §2, before Epics 02–08 add calendars, tokens, and content to it.
Retrofitting a namespace across eight epics' query keys is the expensive version of this decision.

**Alternative rejected**: `queryClient.clear()` on switch. It works, and it is one line, but it also
discards the session and every non-context query, so the whole application re-fetches on a switch
that SC-018 gives two seconds.

### R-27: SVG logos are accepted, screened with the standard library, and served so they cannot execute

**Decision**: Three layers, and **no new dependency**:

1. **Screen before storing.** Reject the upload outright if the bytes contain a `<!DOCTYPE`
   declaration, then parse with `xml.etree.ElementTree` and reject if the tree contains a `script`
   or `foreignObject` element, any attribute beginning `on`, or any `href`/`xlink:href` whose value
   does not begin `#`. Roughly thirty lines in `services/svg_screening.py`, no allowlist to keep
   current.
2. **Serve inertly.** `GET /media/branding/{key}` responds with `Content-Type: image/svg+xml`,
   `X-Content-Type-Options: nosniff`, and `Content-Security-Policy: default-src 'none'; style-src
   'unsafe-inline'`.
3. **Render only through `<img>`.** No `<object>`, no `<embed>`, no inlining into the DOM. A browser
   does not execute script in an SVG loaded as an image, which is the layer that holds even if the
   other two are wrong.

**Rationale**: FR-094 accepts SVG because the epic's validation rules list it; FR-095 requires
active content removed. The constitution's stack rule forbids adding a dependency without an
amendment, so a sanitizer library is not available — and would be disproportionate anyway. The
DOCTYPE pre-check is what makes stdlib parsing safe here: CPython's parsers sit on libexpat, which
by default reaches neither local files nor the network, and recent expat additionally caps entity
expansion amplification — but refusing a DOCTYPE forecloses that entire class before the parser
sees it, rather than depending on which expat the host happens to ship.

**Alternatives rejected**:

- *Reject SVG.* Defensible, and one line — but a logo is exactly the asset a designer hands over as
  a vector, and rasterizing it costs the crispness that made it a vector.
- *Rasterize to PNG on upload.* Needs a renderer (`cairosvg`), which is a stack amendment, and
  throws away the resolution independence.
- *Sanitizer library.* Same amendment problem, for a screening job that is a dozen predicates.

### R-28: Branding lives on `trainer_organizations`, not in a new table

**Decision**: Three columns added to the existing table — `logo_key`, `primary_color`,
`branding_updated_at`.

**Rationale**: Branding is one-to-one with a trainer, the table is already one-to-one with a
trainer, and every read that wants the business name also wants the logo (the join page shows both).
A separate table would be a mandatory join on the hottest read in the feature to hold three columns.
The Phase-2 additions the epic names — a second logo for dark mode, a font choice — are two more
columns, not a growth in cardinality, so the shape does not change under them.

**Alternative rejected**: `trainer_portal_branding` as its own table. Right if branding were
versioned or multi-row; it is neither.

### R-29: The brand colour is stored exactly as chosen; the readable palette is derived at render

**Decision**: `primary_color` stores the hex the trainer picked, validated as `#rrggbb`. The palette
the interface actually paints with is computed by one pure function,
`shared/lib/brand-palette.ts`, which takes the primary colour and returns CSS custom property values
overriding the `DESIGN_TOKENS.md` defaults on a wrapper element. For any surface that carries text,
the function walks the primary colour's lightness until the token foreground reaches a WCAG
relative-luminance contrast ratio of at least 4.5:1; the trainer's exact colour is kept for
non-text accents — borders, the gradient's stops, focus rings.

**Rationale**: FR-098 says the chosen colour drives accents and the gradient; FR-099 says text stays
legible; SC-023 measures 4.5:1. Simply picking black or white text against the raw colour does not
always reach 4.5:1 — there is a narrow band of mid-tones where neither candidate does — so the
surface, not the text, is what must move. Storing the chosen colour unmodified means a later design
change re-derives everything, and it means the colour the trainer sees in the picker is the colour
that comes back when they reopen the settings.

Deriving in the browser rather than the server keeps the stored value canonical and costs nothing:
the computation is a dozen lines of arithmetic on a value already in the session response.

**Alternatives rejected**: storing a derived palette (the derivation becomes data, so a design change
needs a migration); refusing colours that fail contrast (the trainer's brand colour is not
negotiable, and the epic offers no such rejection).

### R-30: Throttling link lookups gets its own durable counter

**Decision**: A new table, `link_lookup_attempts` (`client_ip`, `attempted_at`, `successful`),
counted the same way R-06 counts sign-in attempts: 10 failed lookups from one origin in a trailing
15 minutes refuses further lookups, and the window slides so access resumes without intervention.
Pruned by the maintenance routine that already prunes `sign_in_attempts` and `sessions`.

**Rationale**: FR-071 is per-origin only — there is no second dimension, since an invalid code
identifies nobody. The reasoning for durability is R-06's unchanged: an in-memory counter resets on
deploy and does not exist across processes.

**Alternative rejected**: adding a `kind` column to `sign_in_attempts` and reusing it. It avoids a
table at the cost of migrating a table that already holds production rows and of making every
existing rate-limit query carry a filter it did not need. Two narrow tables with the same shape are
cheaper than one general one here.

### R-31: The player's age is stored as a date of birth

**Decision**: `player_details.date_of_birth` (date, nullable). The registration form collects a date
of birth; the age FR-074 and FR-077 speak of is derived from it at validation and at display.

**Rationale**: An age integer is wrong within twelve months of being written, and it is written once
at registration and read for years — by Epic-02's age-bracketed events and Epic-03's CRM. Storing
the fact and deriving the number keeps FR-077's rule exactly as specified (self ⇒ 18 or over,
dependant ⇒ 1 to 18, evaluated on the derived age at registration) while keeping the stored value
true afterwards. The epic's own data requirements say "age **or** birth date", so this is the
permitted reading.

**Recorded as a refinement, not a silent change**: FR-074 lists "age" among the fields the visitor
supplies. What they supply is a date of birth, which supplies the age. If the client wants a
literal age input, the field changes and the column does not.

### R-32: Gender is a closed set

**Decision**: `Gender` as a `StrEnum` — `male`, `female`, `other`, `prefer_not_to_say` — persisted as
constrained text, matching how `UserRole` and `AccountStatus` are persisted (data-model §1).

**Rationale**: Epic-02 groups events by gender and Epic-03 filters rosters by it, which free text
cannot support without a cleanup pass later. Four values cover the epic's registration form without
prejudging anything; `prefer_not_to_say` exists so the field can be required without forcing a
disclosure.

**Open**: the epic leaves the vocabulary undecided, as it does skill level (data-model §4.3). If the
client names a different set, it is a constraint change and a data migration, not a redesign.

### R-33: The coach half of FR-101 has no data to resolve yet — recorded, not worked around

**Finding, not a decision**: FR-101 requires a trainer's branding to be shown to *that trainer's
coaches*. Which trainer a coach works for is US-01.08, which the spec keeps out of scope, and
`coach_details` accordingly has no employer column (data-model §4.2).

**How the design handles it**: branding resolution is one function,
`branding_service.resolve_for_viewer(user)`, with a branch per role — trainer resolves their own,
`player_parent` resolves the active context's, Super Admin and unauthenticated resolve the platform
default, and **coach returns the platform default with a `TODO(US-01.08)` naming the one line that
changes** when the employer link exists. No column is added speculatively, because nothing would
populate it.

**Why not add the column now**: it would be the first piece of US-01.08 built ahead of its
specification, which Principle I forbids, and an always-null column is not a partial implementation
of anything. This is reported to the user with the plan rather than buried here.

## Consolidated decisions (extension)

| ID | Area | Decision |
|----|------|----------|
| R-21 | Link codes | Stored in clear, 128-bit `token_urlsafe`, unique and indexed |
| R-22 | Link lifecycle | One standing link per trainer, created with the account, backfilled; regenerate revokes and inserts |
| R-23 | Joining | Preview, register, and accept — register is one transaction; duplicate email caught on the index |
| R-24 | Active context | `player_details.active_trainer_user_id`, repaired on read |
| R-25 | Context scoping | Resolved server-side from the caller's row; no `trainer_id` parameter anywhere |
| R-26 | Client caching | `['ctx', trainerId, ...]` key namespace; `removeQueries(['ctx'])` on switch |
| R-27 | SVG | DOCTYPE refusal + stdlib screening + inert serving + `<img>`-only rendering; no new dependency |
| R-28 | Branding storage | Three columns on `trainer_organizations` |
| R-29 | Brand palette | Chosen colour stored as-is; readable surfaces derived in `shared/lib/brand-palette.ts` at ≥4.5:1 |
| R-30 | Link throttling | `link_lookup_attempts`, 10 per 15 minutes per origin, sliding |
| R-31 | Player age | Date of birth stored, age derived |
| R-32 | Gender | Closed four-value enum |
| R-33 | Coach branding | No employer link exists yet; one function branch carries the gap, flagged for US-01.08 |

**No `[NEEDS CLARIFICATION]` markers were raised by the extension.** R-31, R-32, and R-33 are
recorded as decisions the client may overturn cheaply, and R-33 is a dependency rather than a choice.

## Sources (extension)

- CPython documentation, `xml` security notes and `pyexpat` billion-laughs protections, retrieved
  through Context7 (`/python/cpython`, `Doc/library/xml.rst`, `Doc/library/pyexpat.rst`) — used in
  R-27 for the claims that Python's parsers reach neither local files nor the network by default and
  that recent expat caps entity-expansion amplification.
- [WCAG 2.2 — Contrast (Minimum) 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
  for the 4.5:1 ratio and the relative-luminance formula used in R-29.
- [RFC 2606](https://www.rfc-editor.org/rfc/rfc2606) — already cited by the erasure design, and the
  reason `example.com` placeholders stay inert.

Decisions R-21 through R-26, R-28, and R-30 through R-33 follow from the specification and from the
architecture already in place, and are argued from those above rather than from external
documentation.

---

# Phase 0 Research — Extension: Parent/Child Family Accounts & the Approval Workflow

**Date**: 2026-08-27 | **Covers**: spec FR-106 – FR-159, SC-027 – SC-041, User Stories 9–13

**Note on sources**: this slice adds no dependency and asks no question the platform's own shape
cannot answer, so all but two of the decisions below are argued from the specification and from the
architecture already built. The two exceptions are R-40 and R-41, whose claims about SQLite's partial
indexes and about `UPDATE … RETURNING` row counts were checked against the SQLite documentation
through Context7 and are cited at the end.

**A note this part cannot avoid**: unlike the 2026-08-26 extension, this one is **not additive**.
FR-114 moves the subject of a trainer association from the account to the player profile, and there is
no way to hold "one account, several players, each with their own trainers" in a table whose primary
key *is* the account. R-34 and R-35 are therefore migration decisions before they are design
decisions, and they are the riskiest work in the slice. They are stated first for that reason.

---

## Part D — Decisions for the family-accounts extension

### R-34: Player profiles get their own table with a surrogate key; `player_details` is superseded rather than extended

**Decision**: Create `player_profiles` with its own `id` primary key and an `account_user_id`
foreign key, carrying every column `player_details` held plus the family additions
(`kind`, name, photo, the token-spending permission, the optional child sign-in link).
**`player_details` is then dropped**, its rows having been migrated one-to-one. It does not survive as
an empty shell or as a "self profile" special case.

**Rationale**: `player_details.user_id` is both its primary key and its foreign key to `users`
(data-model §4.3). That is a deliberate one-to-one, and it is exactly the constraint FR-106 removes.
Three shapes were available and only one survives contact with the requirements:

| Shape | Verdict |
|---|---|
| Add a surrogate `id` to `player_details` and relax the `user_id` uniqueness | Equivalent in the end state, but SQLite cannot alter a primary key in place, so Alembic's `batch_alter_table` rebuilds the table anyway. The rebuild is the cost, not the rename — and having paid it, the table keeps a name that now means "one of several players", which is what `player_details` does not say. |
| Keep `player_details` for the account holder and add `child_profiles` for children | Rejected outright. Every association, every approval request, and every context would need to reference *either* table, which in SQL means two nullable foreign keys and a check constraint standing in for a discriminated union — the polymorphic-reference shape that Principle II exists to keep out of this codebase. It also duplicates a dozen columns and every validation rule that applies to them. |
| One `player_profiles` table with a `kind` discriminator | **Chosen.** A child and a self-player differ in three rules (age band, whether a sign-in may be granted, whether name and photo are their own) and in nothing structural. A discriminator column plus check constraints expresses that; two tables express a difference that is not there. |

**Consequence for the design**: `PlayerParentDetail` in the contract loses `school`,
`jersey_number`, `skill_level`, `player_name`, `date_of_birth`, `gender`, `is_self`, and
`active_trainer_id` — all of which are now per-profile, not per-account — and keeps only what remains
true of the *account*: the emergency contact detail in `parent_contacts`. This is a **breaking
contract change**, taken deliberately rather than papered over; see R-48.

### R-35: The association's player column is re-pointed to the profile, in three revisions that separate structure from data

**Decision**: Revisions 8, 9, and 10. Revision 8 creates the new tables and adds
`trainer_player_associations.player_profile_id` as **nullable**. Revision 9 is a data migration,
written in SQLAlchemy Core against `op.get_bind()`: one `player_profiles` row per existing
`player_details` row, then `player_profile_id` backfilled on every association, then one
`active_training_contexts` row per player who had a context. Revision 10 makes
`player_profile_id` non-nullable, swaps the unique constraint from
`(trainer_user_id, player_user_id)` to `(trainer_user_id, player_profile_id)`, drops
`player_user_id`, and drops `player_details`.

**Rationale**: the constraint that shapes this is that SQLite has no `ALTER COLUMN` and no
`DROP CONSTRAINT`; every one of those steps is a table rebuild under `batch_alter_table`. Attempting
them in the same revision as the backfill would mean rebuilding a table whose data is mid-flight, and
a failure would leave a half-migrated schema that neither `upgrade` nor `downgrade` describes.
Splitting on the structure/data/constraint boundary means each revision is individually reversible and
each leaves the database in a state the ORM can read:

- After 8, the old and new columns coexist and the application still works unchanged.
- After 9, both are populated and consistent; this is the revision to verify before proceeding.
- After 10, only the new shape remains.

**Boundary this decision does not cross**: revision 9 uses Core `select`/`insert`/`update` constructs,
exactly as revision 7's backfill did, so **the two documented raw-SQL exceptions stay at two**. No new
exception is introduced by this slice.

**Known limitation worth stating plainly**: revision 10 is the point of no return — once
`player_details` is dropped, `downgrade` can restore the table and its rows for self-players but
cannot restore a one-to-one world in which a parent's three children do not fit. The downgrade is
written to fail loudly if any account holds more than one profile, rather than silently discarding
children. A migration that quietly loses data is worse than one that refuses to run.

### R-36: The active context moves off the player's row into its own table, keyed by the signed-in account

**Decision**: A new `active_training_contexts` table keyed by `user_id`, holding a nullable
`player_profile_id` and a nullable `trainer_user_id`. `player_details.active_trainer_user_id`
(R-24) is retired.

**Rationale**: R-24 put the context on the player's row because account and player were the same
thing. They no longer are, and the context is now a *pair* — which profile, and which of that
profile's trainers (FR-117). Two facts force it off the profile row:

- A parent's context names a profile, so it cannot live *on* a profile without one child's row
  holding a pointer to a sibling.
- A child with their own sign-in and the parent both need a context, independently, over the same set
  of profiles. Two viewers, one profile — so the context belongs to the viewer.

Keying by `user_id` gives exactly one context per signed-in account, which is FR-117's "exactly one
pair", and keeps FR-120's cross-device persistence for free, since it is stored against the account
rather than the browser.

**What carries over unchanged**: R-24's resolve-and-repair rule. The stored pair is still never
trusted as read. One service function validates that the profile is still owned by (or is) the
caller, that the association is still `active`, and that the trainer's account is still `active`;
when any of those fails it selects another available pair, writes the correction back, and returns
that. Extending the existing function is the whole change — FR-120 is R-24's rule with a wider
candidate set.

**Alternatives rejected**:

- *Two columns on `users`.* Simple, and wrong: `users` is the account table for four roles, and three
  of them can never hold a training context. A nullable-for-most-rows pair of foreign keys on the
  most-read table in the system is a column that has to be explained every time it is seen.
- *Keep it on the profile and let the parent's context be "the profile I last opened".* Collapses two
  independent viewers onto one stored value, so a child signing in would move their parent's context.

### R-37: A self-player's name and photo stay on the account; only a child's live on the profile

**Decision**: `player_profiles.first_name`, `last_name`, and `photo_key` are `NULL` when
`kind = 'self'` and `NOT NULL` (name) or optional (photo) when `kind = 'child'`, enforced by a check
constraint. For a self profile the platform reads all three from `user_profiles`.

**Rationale**: this continues a decision this document already made rather than making a new one.
Data-model §19.1 introduced `player_name` as nullable precisely "so that correcting the account
holder's name does not leave a stale copy behind for a self-registered player". That reasoning is
unchanged by the family model; what changes is that a *child* has no `user_profiles` row to read from
— a child without a sign-in has no `users` row at all — so a child's name has nowhere else to live.
The check constraint makes the two cases exhaustive and mutually exclusive, so no row can be
ambiguous about which source is authoritative.

**Consequence for the design**: the child photo path and the account photo path are different
endpoints writing different columns, both behind the existing photo storage port. A child's photo is
uploaded by the parent, or by the child themselves under FR-131, and either way it lands on the
profile row.

**Alternative rejected**: *copy the account holder's name onto their self profile at creation and keep
both.* It makes every read uniform, which is the appeal, and it reintroduces exactly the stale-copy
bug §19.1 avoided — with the added twist that the profile copy is the one the trainer's roster shows.

### R-38: A child's sign-in is an ordinary account, and "this is a child" is derived rather than stored twice

**Decision**: Granting a child a sign-in creates a normal `users` row with role `player_parent` and
the parent-supplied email, and records it as `player_profiles.sign_in_user_id` (nullable, unique).
Whether the signed-in account is a child is **derived** — it is the account for which such a profile
row exists — and is loaded in the same statement that resolves the session to its user, not as a
second query.

**Rationale**: the user's answer to the clarification settled the credential (a distinct email, so
FR-001, FR-004, and FR-008 are untouched). What remained open was where "childness" lives. A
`users.account_kind` column would be a second source of truth for a fact the profile table already
states, and the two would diverge the first time a profile was moved or removed — at which point a
revoked child would still be a child by the enum and no longer one by the relationship. Deriving it
means the fact has exactly one home.

**Rationale for loading it eagerly**: the permission gate FR-133 requires runs on every request, so
the derivation must not cost a round trip. The current-user resolution already joins the session to
the account; adding an outer join to `player_profiles` on `sign_in_user_id` makes the caller's identity
carry "child, and of which profile, and whose parent" at no extra query. Enforcement then reads a
value it already has, which is what keeps FR-132's twelve refusals cheap enough to apply
unconditionally.

**Alternatives rejected**:

- *A fifth role, `child`.* Rejected firmly. FR-002 fixes the role set at four and calls a fifth "a
  schema change, not a data entry"; every permission table, every role guard, and every landing-area
  branch in the system enumerates four. A child is a `player_parent` with a narrower permission set,
  which is a rule about the account's relationships, not a new kind of account.
- *A boolean on `users`.* The second-source-of-truth problem above, for one bit.

### R-39: One approval-request table with typed subject columns, not a JSON payload

**Decision**: A single `approval_requests` table. The subject is expressed as **typed nullable
columns** — `trainer_user_id`, `share_link_id`, `amount_minor`, `currency` — with check constraints
tying each to its `kind`: `join_trainer` requires a trainer and forbids an amount; the two financial
kinds require an amount and a currency.

**Rationale**: FR-141's field list and FR-142's three kinds describe one mechanism with a
discriminator, so one table is right (the alternative, a table per kind, triples the resolution logic
and the parent's list becomes a union query). The question worth recording is how the *subject* is
stored, and a JSON column is the obvious wrong answer: Principle II forbids untyped dicts precisely
because a multi-role permission system that gets its subject wrong leaks data, and a JSON
`{"trainer_id": …}` is unvalidated, unindexable, and unreferenced by any foreign key — so nothing
would stop a request naming a trainer that no longer exists. Typed columns give the foreign keys that
make R-42's failure mode (approving a request whose trainer has gone) a checkable condition rather
than a lookup that returns nothing.

**Boundary this decision does not cross**: the two financial kinds get their columns now and their
executor later (R-46). `amount_minor` is an integer of minor currency units, not a float — money in a
binary float is a defect waiting for its first rounding.

**Alternative rejected**: *a generic `subject_type` / `subject_id` pair.* It is the JSON design with
two columns instead of one: no foreign key, no per-kind constraint, and a join that cannot be
expressed.

### R-40: At most one live request per child and subject is a partial unique index, not a service check

**Decision**: A unique index on `(player_profile_id, kind, trainer_user_id)` restricted to
`WHERE status IN ('pending_parent_approval', 'info_requested')`.

**Rationale**: FR-139 and FR-142's duplicate rule say a child who asks twice must land on the request
already waiting. Enforced in the service, that is a read-then-write across two statements, and two
requests arriving together both read "nothing pending" and both insert — which is the edge case
"a child requesting the same thing repeatedly" filling the parent's list. This is the same shape as
the association's unique pair (data-model §17), and it gets the same answer for the same reason: the
service catches the integrity error and returns the existing request, so the rule is **true by
construction rather than checked**. SQLite supports partial indexes, so the restriction to live
statuses — which is what allows a second request after a denial — is expressible directly.

**Consequence for the design**: the index must not cover the terminal statuses, or a child denied once
could never ask again. That is the whole reason the index is partial.

### R-41: Resolution is one conditional update whose row count is the decision

**Decision**: Approving, denying, requesting information, and withdrawing are each a single
`UPDATE … WHERE id = :id AND status IN (:live_statuses) AND expires_at > :now`, and the statement's
**row count** decides the outcome: one row means this caller resolved it, zero means it was already
resolved, already withdrawn, or already lapsed.

**Rationale**: three separate requirements collapse into this one statement, which is why it is worth
recording as a decision rather than left as an implementation detail.

- FR-156's "no one may resolve a request twice" and SC-038's simultaneous-approval case are satisfied
  without a lock, because the second statement matches no row.
- The edge case "expiry racing a decision" is satisfied by the same predicate: a request that has
  passed its deadline cannot be resolved even if the sweep (R-43) has not yet run, so the two paths
  cannot both take effect.
- FR-157's rule that a non-Active parent's requests are unresolvable is one more clause on the same
  `WHERE`, joined to the parent's status.

A read-then-write with an optimistic version column (R-10) would also work, and is what the account
status changes use — but that pattern exists there to report a *conflict* to a Super Admin who needs
to know the row moved. Here the caller needs to know only whether their decision was the one that
counted, which a row count answers directly.

**Consequence for the design**: because the deadline is a stored absolute timestamp (R-43), this
predicate needs no computed expiry and no knowledge of when the request was raised.

### R-42: An approval carries the action out in the same transaction, through a small executor registry

**Decision**: One `ApprovalExecutor` protocol with a `kind` it handles and a method that performs the
action. The approval service resolves the executor for the request's kind and calls it **inside the
same transaction** as the status change. A domain error from the executor rolls back both, leaving the
request live.

**Rationale**: FR-151 requires the action to happen under the parent's permissions and FR-144 requires
it to happen exactly once; both are properties of doing it in the transaction that sets `approved`. The
part that needs a named seam is what happens when it *cannot* be done — FR-151's "must not be recorded
as Approved" and the edge case where a trainer was deactivated while the request waited. A rollback
gives that precisely: the parent is told why, and the request is still waiting for them.

The registry rather than a branch is what makes R-46 honest. `join_trainer` has an executor; the two
financial kinds do not, and an approval of a kind with no registered executor raises a domain error
instead of silently succeeding. When Epic-05 lands it registers two executors and changes nothing
else — the extension point is the reason the kinds can be specified now.

**Alternative rejected**: *approve first, then perform the action in a follow-up step.* Two
transactions, so a failure between them leaves a request marked approved whose action never happened —
the exact state FR-151 forbids.

### R-43: The deadline is an absolute stored timestamp; the sweep notifies, the predicate protects

**Decision**: `expires_at` is written once at creation as `requested_at + 48 hours` and never
recomputed. Two mechanisms then act on it, deliberately: R-41's predicate makes a lapsed request
unresolvable **immediately**, and the existing maintenance routine materializes expiry — setting
`expired` and sending the two notifications FR-155 requires.

**Rationale**: FR-155 asks for two different things and a single mechanism cannot supply both. "The
action is not carried out" must hold the instant the deadline passes, which only a read-time predicate
guarantees; "both the parent and the child are notified" is an outbound side effect, which a predicate
cannot do because nothing is reading at that moment. Pairing them is not redundancy — the predicate is
the correctness guarantee and the sweep is the notification, and neither substitutes for the other.

Storing the deadline rather than deriving it also makes FR-155's last sentence free: a return from
Info Requested to Pending Parent Approval does not restart the clock, because there is no clock to
restart — only a timestamp nobody rewrites.

**Where the sweep lives**: `services/maintenance_service.py` already exists, already holds
`prune_expired_sessions`, `prune_old_sign_in_attempts`, and `prune_old_link_lookup_attempts`, and is
already invoked by the `python -m app.cli prune` subcommand. The application registers **no**
lifespan hook and **no** background task, and this slice adds none. Expiry becomes one more method on
that service and one more line in that subcommand — which is why this decision costs nothing
structurally. The subcommand's help text widens from "expired sessions and old sign-in attempt
records" to name approval expiry too, since a command whose description omits half its effects is how
an operator ends up not scheduling it.

**Known limitation worth stating plainly**: because the routine is invoked externally, notification
timeliness is an operational property, not a code one. If nobody schedules it, requests still become
unresolvable on time — the predicate guarantees that — but the "your request expired" email waits for
the next run. SC-034 is therefore verified by invoking the routine against a fixed clock, and the
deployment obligation to schedule it is recorded in the quickstart rather than assumed.

**Alternatives rejected**:

- *An `asyncio` background task in the app lifespan.* Ties a data-integrity job to process lifetime,
  runs N times under N workers, and adds a lifespan hook the application has so far done without.
- *A scheduler dependency such as APScheduler.* The locked stack forbids an addition, and this would
  need a constitution amendment to schedule one job that `cron` or Task Scheduler already schedules.
- *Lazy expiry alone, with no notification.* Fails FR-155's second half outright.

### R-44: The token-spending permission is a column on the profile, not a settings table

**Decision**: `player_profiles.tokens_without_approval`, boolean, not null, default `false`.

**Rationale**: FR-146 describes exactly one setting, owned by the parent, held per child, defaulting
to requiring approval. A column states that; a `child_settings` table states that there is a growing
set of them, which there is not. The default belongs in the schema rather than in service code because
FR-146's "defaulting to off" is a safety property — a row created by any path, including a future
import, must not accidentally grant unsupervised spending.

**Consequence for the design**: FR-147's "a change never affects a pending request" is automatic. The
setting is consulted when a request is *created*, to decide whether one is needed at all; it is never
read again during resolution, so flipping it cannot approve or deny anything already waiting.

**Boundary this decision does not cross**: FR-145 is enforced independently of this column. A USD
payment consults nothing — the code path that could waive it does not exist, rather than existing and
being guarded by a setting that reads `false`.

### R-45: A possible duplicate child is a refusal the parent can overrule, not a warning the server hopes they read

**Decision**: `POST /me/players` answers a near-duplicate with **409** and a body listing the matching
profiles. The parent re-submits with `acknowledge_possible_duplicate: true`, which creates the profile.

**Rationale**: FR-110 requires a warning that does not block, which is a UI behaviour with no obvious
server shape — and the obvious server shapes are both wrong. Creating the profile and returning a
warning alongside it means the warning arrives after the thing it warns about, so "go back" is no
longer available. Detecting duplicates only in the client means the check is absent from every other
caller and unenforceable in a test. A refusal carrying the reason, plus an explicit acknowledgement to
proceed, makes the two-step visible in the contract and testable without a browser: twins are one
extra field, and a mis-click is caught.

**On what counts as similar**: same account, same date of birth, and a case-insensitive match on the
trimmed first and last name. Deliberately narrow — FR-110's duplicate is a parent submitting the same
child twice, and a fuzzy match that catches "Jon" against "John" would fire on siblings named for the
same relative.

### R-46: The financial kinds ship as schema, rules, and a refusal — not as a pretence

**Finding, not a decision**: FR-142 requires the USD and token kinds to have their rules and recorded
data in place while their execution belongs to Epic-05, and FR-142's last clause requires that such a
request "MUST NOT be marked approved until that act can be performed".

**How the design handles it**: the kinds exist in the enum, the columns exist and are constrained, the
approval rules (FR-145, FR-146) are enforced at request creation, and **no endpoint in this feature
creates a request of either kind**. Should one arrive by any route, R-42's registry has no executor for
it and approval raises a domain error rather than recording an approval whose payment never happened.

**Why not stub the executor now**: a stub that "succeeds" would satisfy the type and violate the
requirement, and the first test to pass against it would be a test asserting that money moved when it
did not. Principle I's prohibition on code ahead of an approved spec applies to Epic-05's payment
execution as much as to anything else.

**This is a known and intended gap between FR-142 as written and what ships**, in the same spirit as
R-33's coach-branding gap: recorded here, visible in the plan's Complexity Tracking, and closed by
Epic-05 registering two executors.

### R-47: Context-scoped query keys become profile-aware

**Decision**: `ctxKeys` moves from `['ctx', trainerId, …]` to `['ctx', profileId, trainerId, …]`, and
switching context still removes the whole `['ctx']` namespace.

**Rationale**: R-26 fixed this convention early and said why — so that User Story 7's isolation rule
would not have to be retrofitted across eight epics. That reasoning now pays out, and demands a
change: FR-117 makes the isolation boundary a *pair*, so a key naming only the trainer would collide
between two siblings training with the same trainer, and a cached roster or calendar would leak from
one child's view into the other's. Adding the profile to the namespace is a two-line change today
because the namespace still holds one entry; after Epic-02 it would be a sweep across every
context-scoped hook.

**Recorded as a refinement, not a silent change**: R-26 stands in full — the namespace and the
drop-on-switch behaviour are unchanged. Only the key's shape widens, and the reason is the same reason
R-26 gave for choosing a namespace at all.

### R-48: Sibling isolation rides the context dependency; no endpoint takes a profile id it has not validated

**Decision**: The `get_trainer_context` dependency becomes `get_training_context`, returning a
validated `(player_profile_id, trainer_user_id)` pair. Every context-scoped endpoint depends on it and
takes **no** profile identifier from the caller. Endpoints that must name a profile — the family
management routes under `/me/players/{profile_id}` — validate ownership in the service against the
caller's account.

**Rationale**: R-25 established that no endpoint takes a `trainer_id`, because dozens of
context-scoped endpoints are coming and one that forgets to validate is a cross-tenant read. FR-117
adds a second axis with exactly the same hazard and a nastier failure mode: a sibling is on the *same
account*, so an ownership check that stops at "does this profile belong to the caller's account?"
passes for a child reading their brother's schedule. The dependency therefore validates the pair
against the caller's *kind* — a parent may name any profile on their account, a child may name only
the profile their sign-in is attached to — which is FR-132's sibling prohibition and FR-119's switcher
rule enforced in one place rather than at each caller.

**Consequence for the design**: SC-028 and SC-040 are testable as a sweep over every context-scoped
route with a two-child fixture, which is the shape the existing cross-trainer isolation sweep already
has. A permission matrix cannot replace it, for the reason the 2026-08-26 extension already recorded:
"one trainer's data never appears in another's response body" is a different failure from "a role
cannot reach an action", and sibling leakage is the same different failure.

**Consequence for the API's shape** — worth stating because it looks arbitrary otherwise: CI enforces
R-25 with a grep that fails the build on any `trainer_id` appearing in a `Path(` or `Query(`
declaration outside the admin router. The family-management routes legitimately name a trainer, since
FR-125 and FR-126 are a parent deliberately choosing one, so they name it **in a request body** — the
channel `PUT /me/trainer-context` already uses — and remove an association by its **own identifier**
(`DELETE /me/players/{profile_id}/trainers/{association_id}`) rather than by the trainer's. That is
better addressing regardless, and it keeps the guard meaningful instead of accumulating the first
exception that would teach the next reader to add another.

### R-49: The contract changes shape rather than growing a parallel one

**Decision**: `info.version` goes to **1.2.0**. `PlayerParentDetail` loses the player fields (R-34),
`TrainerPlayerSummary` gains the profile identity and the responsible parent's contact detail, and
`GET /me/trainers` is replaced by `GET /me/contexts` returning profile-and-trainer pairs. No
versioned duplicate of any operation is kept.

**Rationale**: these are breaking changes and the honest move is to make them once, while the only
consumer is this repository's own frontend, which ships in the same commit. A parallel v1 shape would
mean two roster serializers and two context endpoints to keep in step for the benefit of no external
caller — and the contract test asserts the generated document against this file, so a divergence
between them fails the build rather than reaching anyone.

**Boundary this decision does not cross**: the URL prefix stays `/api/v1`. This is a pre-release
contract revision, not a second public version, and inventing `/api/v2` for a schema the outside world
has never seen would leave a permanent scar for a migration that costs nothing today.

### R-50: A child's access follows the parent's status without a status of its own

**Decision**: A child sign-in is refused, and its sessions revoked, whenever the owning parent's
account is not Active. This is **evaluated from the parent's status**, not copied onto the child's
row. Revocation of a child's sign-in by the parent (FR-134) is separate and *is* stored, as clearing
`sign_in_user_id` and revoking that account's sessions.

**Rationale**: FR-136 requires suspension to follow the parent in both directions — "MUST restore them
when the parent is reactivated". A copied status would need the reverse propagation to be written,
tested, and to not miss the erasure path; a derived one restores automatically because there was
nothing to restore. The child's account keeps its own `status` for its own lifecycle (FR-135's rule
that removing a profile ends the sign-in), so the two facts stay separable: *this account is
switched off* and *this account's responsible adult is switched off* are different, and only the first
belongs on the child's row.

**Consequence for the design**: the check joins to the parent in the same statement R-38 already
extended, so it costs nothing additional. Deactivating a parent revokes child sessions in the same
transaction as the status change, which is how FR-012's "the moment" and SC-041's one-minute ceiling
stay true by construction — the mechanism data-model §5 already uses.

### R-51: Notifications fan in to the parent, once per event

**Decision**: Every notification about a child is addressed to the parent's account email (FR-130).
Where one event concerns several children, one message names them all rather than one message per
child; where a child repeats an action that has already produced a pending request, no further message
is sent (FR-139).

**Rationale**: the edge case "notification storms" is the only requirement here, and it is a real
failure mode rather than a nicety: a parent with four children who each follow the same trainer's link
receives four emails about one decision, and a child who taps a blocked link five times sends five.
The first is answered by addressing the *event* rather than the child; the second is answered for free
by R-40's index, since no second request exists to notify about.

**Boundary this decision does not cross**: R-11's design is unchanged — one `EmailSender` port, SMTP
plus a filesystem sink, sent in-request with the failure surfaced. D-06's decision to add no outbox
and no retry worker stands. A failed notification does not roll back the request it describes, exactly
as FR-079 already established for the join confirmation.

---

## Consolidated decisions (family accounts)

| ID | Area | Decision |
|----|------|----------|
| R-34 | Player profiles | New `player_profiles` table with a surrogate key and a `kind` discriminator; `player_details` dropped |
| R-35 | Migration | Three revisions — structure, data, constraints — with a downgrade that refuses to discard children |
| R-36 | Active context | Own table keyed by the signed-in account, holding a profile-and-trainer pair |
| R-37 | Names and photos | A self profile reads the account's; a child's live on the profile, enforced by a check constraint |
| R-38 | Child sign-in | An ordinary `player_parent` account; childness derived, loaded with the current user |
| R-39 | Approval subject | One table, typed nullable columns per kind, no JSON payload |
| R-40 | Duplicate requests | Partial unique index over the live statuses |
| R-41 | Resolution | One conditional update; the row count is the decision |
| R-42 | Approval execution | Executor registry, same transaction, rollback leaves the request live |
| R-43 | Expiry | Stored absolute deadline; predicate protects immediately, maintenance routine notifies |
| R-44 | Token permission | A boolean column on the profile, defaulting to requiring approval |
| R-45 | Duplicate children | 409 plus an explicit acknowledgement, not a post-hoc warning |
| R-46 | Financial kinds | Schema and rules now, no executor, approval refused rather than faked |
| R-47 | Query keys | `['ctx', profileId, trainerId, …]` — R-26's namespace widened |
| R-48 | Sibling isolation | Validated in the context dependency, which no caller can bypass |
| R-49 | Contract | Breaking changes made once at 1.2.0; no parallel shape, no `/api/v2` |
| R-50 | Child suspension | Derived from the parent's status, not copied |
| R-51 | Notifications | Addressed to the parent, one per event |

**No `[NEEDS CLARIFICATION]` markers were raised by this extension.** The two questions that could
have become markers — what a child signs in with, and how the approval workflow is bounded while
Epic-02 and Epic-05 are absent — were put to the user before the specification was written and are
recorded in `checklists/requirements.md`; R-38 and R-46 implement those answers.

## Sources (family accounts)

- SQLite documentation, [Partial Indexes](https://www.sqlite.org/partialindex.html), retrieved through
  Context7 — used in R-40 for the claim that a unique index may be restricted by a `WHERE` clause, on
  which the "one live request per child and subject" rule depends.
- SQLite documentation, [UPDATE](https://www.sqlite.org/lang_update.html) and
  [ALTER TABLE](https://www.sqlite.org/lang_altertable.html) — used in R-41 for conditional-update
  row-count semantics and in R-35 for the absence of `ALTER COLUMN` and `DROP CONSTRAINT`, which is
  what forces the three-revision split.
- [Alembic — Running "Batch" Migrations for SQLite](https://alembic.sqlalchemy.org/en/latest/batch.html)
  for the table-rebuild behaviour R-35 plans around.

Decisions R-34, R-36 through R-39, and R-42 through R-51 follow from the specification and from the
architecture already in place, and are argued from those above rather than from external
documentation.
