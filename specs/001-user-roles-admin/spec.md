# Feature Specification: User Roles, Authorization & Super Admin User Management

**Feature Branch**: `001-user-roles-admin`

**Created**: 2026-08-19

**Status**: Draft

**Input**: User description: "Read file Task/Epics/Epic-01_User_Management_Authentication_SPEC.md. Create specification (spec.md) only for initial Database structure (4 roles), authorizations and Super Admin functionality (US-01.01, US-01.11, US-01.12, US-01.13). Ignore other user stories for now."

**Source Epic**: Epic-01 — User Management & Authentication. This specification covers the
foundational account structure, sign-in and permission enforcement, plus epic stories US-01.01,
US-01.11, US-01.12, and US-01.13. All other Epic-01 stories are explicitly out of scope
(see Out of Scope).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Role-Separated Sign-In (Priority: P1)

Every person who uses the platform holds an account tied to exactly one role — Super Admin,
Trainer, Coach, or Player/Parent — and signs in with an email address and a password. After signing
in, they land in the area belonging to their role and can reach only the capabilities their role
permits. Someone whose account has been switched off cannot get in at all, and is told to contact
support rather than being left guessing.

**Why this priority**: Nothing else in the platform can be built or demonstrated until accounts,
roles, and permission boundaries exist. Every later story in this feature and every other epic
depends on knowing who is asking and what they are allowed to do.

**Independent Test**: Seed one account per role, sign in as each, and confirm each one reaches its
own landing area and is refused when it attempts an action reserved for another role. Confirm a
switched-off account cannot sign in. This delivers a working, secure multi-role sign-in even if no
other story ships.

**Acceptance Scenarios**:

1. **Given** an active account with a correct email and password, **When** the person signs in,
   **Then** they are admitted and taken to the area belonging to their role.
2. **Given** an account, **When** the person submits a wrong password or an unregistered email,
   **Then** sign-in is refused with a single message that does not reveal whether the email exists.
3. **Given** a signed-in Trainer, **When** they attempt an action reserved for Super Admins,
   **Then** the action is refused and no data is changed, whether the attempt comes through the
   interface or by addressing the platform directly.
4. **Given** a signed-in Coach, **When** they attempt to read or change another person's profile,
   **Then** the attempt is refused.
5. **Given** an account whose status is Inactive or Deleted, **When** the person submits correct
   credentials, **Then** sign-in is refused with the message that the account is deactivated and
   support should be contacted.
6. **Given** a signed-in person, **When** they sign out, **Then** their session ends and reusing the
   previous session no longer grants access.
7. **Given** repeated failed sign-in attempts for the same email in a short period, **When** the
   attempts exceed the allowed rate, **Then** further attempts are temporarily refused.
8. **Given** a session that has been idle beyond the inactivity limit, **When** the person acts
   again, **Then** they are asked to sign in once more.

---

### User Story 2 - Super Admin Creates a Trainer Account (Priority: P1)

A Super Admin opens the platform's user directory, creates a new Trainer account by entering the
business name, the trainer's name, email address, and phone number, and the new trainer receives an
email that lets them set their own password and sign in for the first time. Trainers never sign
themselves up; the Super Admin is the only route in, which keeps quality and billing under control.

**Why this priority**: Trainers are the platform's paying customers and the owners of every training
organization. Until a Super Admin can create one, no organization exists and no downstream epic can
be demonstrated.

**Independent Test**: Sign in as a Super Admin, create a Trainer, verify the invitation is sent,
follow the setup link to choose a password, and sign in as the new Trainer. Also attempt to create
a second account with the same email and confirm the clear rejection.

**Acceptance Scenarios**:

1. **Given** a signed-in Super Admin on the user directory, **When** they choose to create a user,
   select the Trainer role, supply business name, trainer name, email, and phone, and submit,
   **Then** the account is created with status Active and appears in the directory.
2. **Given** a newly created Trainer account, **When** creation succeeds, **Then** an invitation
   email is sent to that address containing a single-use setup link.
3. **Given** a valid, unused setup link, **When** the trainer opens it and chooses a password
   meeting the strength rules, **Then** the password is set, the link is consumed, and they can
   sign in.
4. **Given** a setup link that has already been used or has passed its expiry, **When** the trainer
   opens it, **Then** they are told the link is no longer valid and are offered a way to request a
   new one.
5. **Given** an email address already belonging to any account in any status, **When** the Super
   Admin submits it, **Then** creation is refused with a message naming the duplicate email as the
   cause, and no partial account is left behind.
6. **Given** a submission missing a required field or containing a malformed email or phone number,
   **When** it is submitted, **Then** each offending field is identified and nothing is saved.
7. **Given** a signed-in Trainer, Coach, or Player/Parent, **When** they attempt to create a user
   account, **Then** the attempt is refused.
8. **Given** a Trainer account was created, **When** an administrator reviews the audit trail,
   **Then** it records which Super Admin created the account, when, and for which email.
9. **Given** a signed-in Super Admin creating a user, **When** they select the Coach or
   Player/Parent role instead of Trainer, **Then** the account is created and invited by the same
   flow, holding no organizational relationship to any trainer.

---

### User Story 3 - Any User Edits Their Own Profile (Priority: P2)

Any signed-in person — whatever their role — can open their own profile, correct their name, phone
number, and photo, fill in the extra details that apply to their role, and save. Fields that
identify or classify the account, such as the sign-in email, the role itself, and a player's
trainer-assigned skill level, are visible but not editable here.

**Why this priority**: Profile self-service is what makes the account records trustworthy and
removes routine administrative requests, but the platform is usable without it, so it follows the
two foundational stories.

**Independent Test**: Sign in as each of the four roles in turn, change the editable fields
including the photo, save, sign out and back in, and confirm the changes persisted. Confirm the
read-only fields cannot be changed even when the request is made directly rather than through the
form.

**Acceptance Scenarios**:

1. **Given** a signed-in person of any role, **When** they open their profile, **Then** they see
   their current details with editable and read-only fields clearly distinguished.
2. **Given** the profile form, **When** they change first name, last name, or phone number and
   save, **Then** the changes are stored and a confirmation is shown.
3. **Given** the profile form, **When** they upload a photo in an accepted format and within the
   size limit, **Then** the photo is stored, a smaller version suitable for lists is produced, and
   both the profile and any place their photo appears show the new image.
4. **Given** a photo that is too large or of an unsupported type, **When** it is uploaded, **Then**
   it is rejected with a message stating the accepted formats and size limit, and the previous
   photo remains.
5. **Given** a signed-in Player/Parent, **When** they open their profile, **Then** the school and
   jersey number fields are available in addition to the common fields.
6. **Given** a signed-in Coach, **When** they open their profile, **Then** biography,
   credentials, certifications, and a setting controlling whether their profile is publicly visible
   are available.
7. **Given** a signed-in Trainer, **When** they open their profile, **Then** business name and
   organization details — address, website, description — are available.
8. **Given** any signed-in person, **When** they attempt to change their own sign-in email, role,
   account status, or trainer-assigned skill level through the profile, **Then** the attempt is
   refused and the stored values are unchanged.
9. **Given** a phone number in an unrecognized format or a cleared required name field, **When**
   save is attempted, **Then** the offending field is identified and nothing is saved.
10. **Given** a signed-in person, **When** they open the profile of a different account, **Then**
    the attempt is refused unless they are a Super Admin.

---

### User Story 4 - Super Admin Deactivates and Reactivates a User (Priority: P2)

A Super Admin can switch off any account from the user directory. The person can no longer sign in,
but every record of what they did — attendance, payments, referrals, roster entries — stays exactly
where it was, marked as belonging to an inactive person. The same Super Admin can switch the account
back on again, restoring access unchanged.

**Why this priority**: Deactivation is the everyday tool for handling departures, non-payment, and
misconduct without destroying the history the business runs its reporting on. It is needed before
launch but after accounts and creation exist.

**Independent Test**: Deactivate an account with existing history, confirm sign-in is refused,
confirm the person still appears in historical records marked inactive and that reporting totals are
unchanged, then reactivate and confirm sign-in works again.

**Acceptance Scenarios**:

1. **Given** a signed-in Super Admin viewing an active account, **When** they choose to deactivate
   it, **Then** they must confirm through a prompt stating the person will be unable to sign in
   while all historical data is preserved.
2. **Given** the confirmation is given, **When** it completes, **Then** the account status becomes
   Inactive and the directory shows it as such.
3. **Given** a deactivated account, **When** the person submits correct credentials, **Then**
   sign-in is refused with the deactivated-account message.
4. **Given** a deactivated account with an open session, **When** the next action is attempted on
   that session, **Then** it is refused and the session ends.
5. **Given** a deactivated person who has historical records, **When** those records are viewed,
   **Then** the person still appears, visually marked as inactive, and reporting totals that
   included them are unchanged.
6. **Given** a signed-in Super Admin viewing an inactive account, **When** they choose to
   reactivate it, **Then** the status returns to Active and the person can sign in with their
   existing password.
7. **Given** any non-Super-Admin, **When** they attempt to deactivate or reactivate any account,
   **Then** the attempt is refused.
8. **Given** a Super Admin, **When** they attempt to deactivate their own account, **Then** the
   attempt is refused with an explanation.
9. **Given** a deactivation or reactivation completed, **When** the audit trail is reviewed,
   **Then** it records who acted, on which account, and when.

---

### User Story 5 - Super Admin Erases a User's Personal Information (Priority: P3)

When someone exercises their right to be forgotten, a Super Admin permanently erases their personal
information from the platform. Their name becomes "Deleted User", their email and phone are replaced
or cleared, and their photo reverts to a default. Everything the business needs for reporting and
legal defensibility survives: the session they attended, the payment they made, the totals they
contributed to. The action cannot be undone, and a record of who performed it and why is retained.

**Why this priority**: This is a legal obligation rather than a daily operation, and it is the most
destructive action in the feature, so it ships last — after the states it operates on are proven.

**Independent Test**: Issue a deletion against an account with attendance and payment history,
confirm the personal fields are anonymized, confirm the historical records still exist attributed to
"Deleted User" with unchanged totals, confirm the account can never be reactivated, and confirm the
compliance record captures the original identity, the acting administrator, the reason, and the time.

**Acceptance Scenarios**:

1. **Given** a signed-in Super Admin viewing an account, **When** they choose to delete it, **Then**
   they must confirm through a prominent warning stating that personal information will be removed,
   historical records will show "Deleted User", and the action cannot be undone.
2. **Given** the deletion prompt, **When** the Super Admin confirms, **Then** a reason for the
   deletion must be supplied before the action proceeds.
3. **Given** deletion completes, **When** the account is inspected, **Then** the displayed name is
   "Deleted User", the email is replaced with a non-routable placeholder unique to that account, the
   phone number and other personal identifiers are cleared, and the photo is the default avatar.
4. **Given** deletion completes, **When** historical records are viewed, **Then** attendance,
   payments, and roster entries still exist attributed to "Deleted User" with their original dates
   and amounts.
5. **Given** deletion completes, **When** reporting totals are compared with their pre-deletion
   values, **Then** participant counts, revenue sums, and attendance rates are identical.
6. **Given** a deleted account, **When** the person attempts to sign in with their former
   credentials, **Then** sign-in is refused.
7. **Given** a deleted account, **When** a Super Admin attempts to reactivate it or edit its
   profile, **Then** the attempt is refused because the erasure is permanent.
8. **Given** a deleted account's former email address, **When** a Super Admin creates a new account
   with that same address, **Then** creation succeeds, because the placeholder released the original
   address.
9. **Given** deletion completes, **When** the compliance record is reviewed, **Then** it holds the
   original account identifier, the original email address, the acting Super Admin, the stated
   reason, and the timestamp.
10. **Given** any non-Super-Admin, **When** they attempt to delete any account, **Then** the attempt
    is refused.
11. **Given** a Super Admin, **When** they attempt to delete their own account, **Then** the attempt
    is refused with an explanation.

---

### Edge Cases

- **Last Super Admin**: What happens when the only remaining active Super Admin account is
  deactivated or deleted? The platform must refuse, because no one would be left able to administer
  it.
- **Concurrent status change**: What happens when two Super Admins act on the same account at the
  same time — one deactivating, one deleting? One action must win and the other must be told the
  account changed underneath it, rather than both partially applying.
- **Deletion of an already inactive account**: Erasure must be permitted from either Active or
  Inactive status and must always land on Deleted.
- **Deactivating an already inactive account**: The action is refused or reported as no change; it
  never produces a second deactivation record.
- **Session held during deletion**: An open session belonging to a person being deleted must stop
  working immediately, not at its next natural expiry.
- **Setup link after deactivation**: An unused invitation link for an account that was deactivated
  before first sign-in must stop working.
- **Duplicate email against a deleted account's placeholder**: Creating an account whose email
  collides with a generated placeholder address must be prevented.
- **Profile photo replacement**: When a photo is replaced, the previously stored image and its
  smaller version must not remain reachable.
- **Rate limiting a legitimate user**: A person who mistypes their password several times must be
  able to get back in after a stated cooling-off period rather than being locked out permanently.
- **Very large directory**: The user directory must stay usable when it holds tens of thousands of
  accounts, which means the list is paged rather than delivered whole.
- **Role reserved for later onboarding**: Coach and Player/Parent accounts arrive through
  invitation flows that are out of scope here; the platform must still store and enforce those two
  roles correctly so that this feature does not have to change when those flows are added.

## Requirements *(mandatory)*

### Functional Requirements

**Accounts, roles, and statuses**

- **FR-001**: System MUST store every person as a single account identified by a unique email
  address, holding a securely hashed password, exactly one role, exactly one status, the timestamp
  of the last successful sign-in, and creation and last-modified timestamps.
- **FR-002**: System MUST support exactly four roles — Super Admin, Trainer, Coach, and
  Player/Parent — and MUST reject any account whose role is absent or outside that set.
- **FR-003**: System MUST support exactly three account statuses — Active, Inactive, and Deleted —
  with Active the only status permitting sign-in, and MUST permit only these transitions:
  Active↔Inactive, Active→Deleted, and Inactive→Deleted. Deleted MUST be terminal.
- **FR-004**: System MUST enforce email uniqueness across all accounts regardless of status, so a
  deactivated account's address cannot be reused while that account exists.
- **FR-005**: System MUST store a common profile for every account holding first name, last name,
  phone number, and profile photo reference, with first and last name required.
- **FR-006**: System MUST store the role-specific profile details that each role's own profile view
  exposes: business name plus organization address, website, and description for Trainers;
  biography, credentials, certifications, and public-visibility preference for Coaches; school and
  jersey number for Players; and emergency contact details for Parents.
- **FR-007**: System MUST record a trainer-assigned skill level on player profiles as a value the
  player cannot edit, reserving its assignment to a later feature.

**Authentication and session handling**

- **FR-008**: System MUST authenticate a person by email address and password, admitting them only
  when the credentials match an account whose status is Active.
- **FR-009**: System MUST NEVER store or transmit a password in a recoverable form, and MUST use an
  industry-standard one-way hash with a per-account salt.
- **FR-010**: System MUST return one indistinguishable failure message for an unknown email, a
  wrong password, and a correct password against a non-Active account, except that a non-Active
  account MUST be told its access has been withdrawn and support should be contacted.
- **FR-011**: System MUST issue a session on successful sign-in, MUST expire that session after 7
  days of inactivity, and MUST invalidate it on sign-out.
- **FR-012**: System MUST invalidate every existing session for an account the moment its status
  leaves Active.
- **FR-013**: System MUST rate-limit sign-in attempts per email address and per origin, refusing
  further attempts for a stated cooling-off period once the limit is exceeded, and MUST allow
  attempts again automatically once that period passes.
- **FR-014**: System MUST require passwords of at least 12 characters and MUST reject a password
  that appears in a list of commonly breached passwords.

**Authorization**

- **FR-015**: System MUST enforce every permission rule when a request is received, independently of
  the interface, so that hiding a control is never the only barrier protecting an action.
- **FR-016**: System MUST restrict account creation, deactivation, reactivation, deletion, and
  viewing of the platform-wide user directory to Super Admins.
- **FR-017**: System MUST allow every signed-in person to read and edit their own profile, and MUST
  refuse any attempt to read or edit another account's profile unless the requester is a Super
  Admin.
- **FR-018**: System MUST refuse any request carrying no valid session, an expired session, or a
  session belonging to a non-Active account.
- **FR-019**: System MUST present each signed-in person a landing area determined by their role and
  MUST expose to them only the actions their role permits.
- **FR-020**: System MUST refuse and record any request in which a person attempts an action outside
  their role's permissions.

**Super Admin creates a Trainer account (US-01.01)**

- **FR-021**: Super Admins MUST be able to create a Trainer account by supplying business name,
  trainer first and last name, email address, and phone number, all of which are required.
- **FR-022**: System MUST validate email format and phone format on creation, and MUST identify each
  invalid or missing field individually rather than reporting a single generic failure.
- **FR-023**: System MUST refuse creation when the email address already belongs to any account, and
  MUST state the duplicate email as the reason.
- **FR-024**: System MUST create the account with status Active and no usable password, and MUST NOT
  leave a partially created account behind when any step fails.
- **FR-025**: System MUST send the new trainer an invitation email containing a single-use setup
  link that expires 24 hours after issue, and MUST NOT include a password in that email.
- **FR-026**: System MUST require the invited trainer to choose their own password before their
  first sign-in succeeds.
- **FR-027**: System MUST consume a setup link on first successful use, and MUST refuse a link that
  is already used, expired, or belongs to a non-Active account, offering a way to request a
  replacement.
- **FR-028**: Super Admins MUST be able to issue a fresh invitation to an account that has not yet
  set a password, which invalidates any earlier outstanding link for that account.
- **FR-029**: System MUST record in the audit trail which Super Admin created each account, when,
  the role assigned, and the email address used.
- **FR-030**: Super Admins MUST be able to assign any of the four roles when creating an account, and
  every created account MUST follow the same invitation-driven first-password flow regardless of the
  role assigned. An account created this way carries no organizational relationships — a Coach is
  attached to no trainer and a Player/Parent to no trainer — because those relationships belong to
  onboarding flows outside this feature.

**Self-service profile editing (US-01.11)**

- **FR-031**: Every signed-in person MUST be able to view their own profile with editable and
  read-only fields visually distinguished.
- **FR-032**: Every signed-in person MUST be able to change their first name, last name, phone
  number, profile photo, and the role-specific fields defined for their own role, and MUST receive
  confirmation when the change is stored.
- **FR-033**: System MUST treat sign-in email, role, account status, account creation date, and
  trainer-assigned skill level as read-only in the profile, and MUST refuse any attempt to change
  them there regardless of how the request is submitted.
- **FR-034**: System MUST accept profile photos in common web image formats up to 5 MB, MUST produce
  a smaller version suitable for list and roster display, and MUST reject anything outside those
  limits with a message naming the accepted formats and size.
- **FR-035**: System MUST render a default avatar for any account without a stored photo.
- **FR-036**: System MUST validate name and phone format on save and MUST leave the stored profile
  untouched when validation fails.

**Deactivation and reactivation (US-01.12)**

- **FR-037**: Super Admins MUST be able to deactivate an Active account, and the platform MUST
  require an explicit confirmation stating that the person will be unable to sign in while all
  historical data is preserved.
- **FR-038**: System MUST move a deactivated account to status Inactive and MUST preserve every
  associated record — attendance, payments, referrals, roster entries — unchanged.
- **FR-039**: System MUST continue to show an inactive person in historical records and rosters,
  visibly marked as inactive, and MUST leave every reporting total that included them unchanged.
- **FR-040**: Super Admins MUST be able to reactivate an Inactive account, returning it to Active
  with its existing password and profile intact.
- **FR-041**: System MUST refuse deactivation or deletion of an account when it is the last Active
  Super Admin, and MUST refuse any Super Admin's attempt to deactivate or delete their own account.
- **FR-042**: System MUST record every deactivation and reactivation in the audit trail with the
  acting Super Admin, the affected account, and the time.

**Privacy erasure (US-01.13)**

- **FR-043**: Super Admins MUST be able to permanently erase an account's personal information from
  either Active or Inactive status, and the platform MUST require confirmation through a prominent
  warning that personal information will be removed, historical records will read "Deleted User",
  and the action cannot be undone.
- **FR-044**: System MUST require a stated reason before an erasure proceeds.
- **FR-045**: System MUST, on erasure, replace the displayed name with "Deleted User", replace the
  email with a non-routable placeholder unique to that account, clear the phone number and all other
  personal identifiers, discard the stored photo so the default avatar is shown, and set the status
  to Deleted.
- **FR-046**: System MUST preserve every historical record belonging to an erased account with its
  original dates, amounts, and outcomes, attributed to "Deleted User".
- **FR-047**: System MUST leave every reporting total — participant counts, revenue sums, attendance
  rates — numerically identical before and after an erasure.
- **FR-048**: System MUST treat erasure as irreversible, refusing reactivation, profile editing, and
  sign-in for a Deleted account.
- **FR-049**: System MUST retain a compliance record for each erasure holding the original account
  identifier, the original email address, the acting Super Admin, the stated reason, and the
  timestamp, and MUST keep that record readable only by Super Admins.
- **FR-050**: System MUST allow a new account to be created with an erased account's former email
  address.

**User directory**

- **FR-051**: Super Admins MUST be able to browse a platform-wide directory of accounts showing for
  each one the name, email address, role, status, and creation date.
- **FR-052**: System MUST page the directory and MUST allow Super Admins to search it by name or
  email and filter it by role and status, so that it remains usable at tens of thousands of
  accounts.
- **FR-053**: System MUST offer the create, deactivate, reactivate, and delete actions from the
  directory, showing only those valid for the selected account's current status.

**Audit trail**

- **FR-054**: System MUST record every administrative action on an account — creation, invitation,
  deactivation, reactivation, erasure — with the acting account, the affected account, the action,
  the time, and any stated reason.
- **FR-055**: System MUST make audit entries append-only, so no one can alter or remove them through
  the platform.
- **FR-056**: System MUST NOT expose internal error detail, stored credential material, or system
  diagnostics to any client under any failure condition.

### Key Entities *(include if feature involves data)*

- **User Account**: One person's identity and means of entry. Holds unique email, hashed password,
  role, status, last sign-in time, and creation and update times. Owns exactly one profile.
- **Role**: The fixed set of four permission classes — Super Admin, Trainer, Coach, Player/Parent.
  Determines the landing area and every permission decision. One per account.
- **Account Status**: The fixed set of three lifecycle states — Active, Inactive, Deleted —
  governing whether sign-in is possible and whether the account can still be changed.
- **User Profile**: The personal detail shared by every role — names, phone number, photo reference.
  Exactly one per account; anonymized rather than removed on erasure.
- **Trainer Organization Detail**: The business identity attached to a Trainer account — business
  name, address, website, description. Later epics extend this with billing and fee information.
- **Coach Detail**: A Coach's professional presentation — biography, credentials, certifications,
  and whether the profile is publicly visible. The single-trainer assignment that Epic-01 also
  describes is out of scope here.
- **Player Detail**: A player's participation attributes — school, jersey number, and the
  trainer-assigned skill level that the player cannot edit. Parent/child linkage is out of scope
  here.
- **Parent Contact Detail**: Emergency contact information held against a Player/Parent account.
- **Session**: An admitted person's continuing access, with issue time, last-activity time, and
  expiry. Ends on sign-out, on inactivity, and whenever the account leaves Active status.
- **Credential Setup Invitation**: A single-use, time-limited permission to set a password for an account
  that has none, tied to one account, carrying issue time, expiry, and consumption state.
- **Administrative Audit Entry**: An append-only record of one administrative action — the acting
  account, the affected account, the action, the time, and any stated reason.
- **Erasure Compliance Record**: The legally retained trace of one privacy erasure — original
  account identifier, original email address, acting Super Admin, stated reason, timestamp.
  Readable only by Super Admins.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person signing in with valid credentials reaches their role's landing area within 2
  seconds.
- **SC-002**: 100% of attempts to perform an action outside the requester's role are refused when
  submitted directly to the platform rather than through its interface, verified by a permission
  test covering every role against every restricted action.
- **SC-003**: A Super Admin can create a working Trainer account, from opening the directory to the
  invitation being sent, in under 2 minutes.
- **SC-004**: An invited trainer can set their password and reach their own area on the first
  attempt in at least 95% of cases, with no need to contact support.
- **SC-005**: Saving a profile change, including a photo upload, completes and confirms within 1
  second for the non-photo fields.
- **SC-006**: The user directory returns its first page within 3 seconds when the platform holds
  10,000 accounts.
- **SC-007**: A deactivated person is unable to sign in and every open session of theirs stops
  working within 1 minute of the deactivation.
- **SC-008**: Reporting totals — participant count, revenue sum, attendance rate — are numerically
  identical before and after a deactivation and after an erasure, verified against a fixed data set.
- **SC-009**: After an erasure, no query available through the platform returns the erased person's
  former name, email address, or phone number, while 100% of their historical records remain present
  as "Deleted User".
- **SC-010**: 100% of account creations, invitations, deactivations, reactivations, and erasures
  produce an audit entry naming the actor, the target, and the time.
- **SC-011**: Automated sign-in attempts against a single email address are throttled after no more
  than 10 consecutive failures, and legitimate access resumes automatically within 15 minutes.
- **SC-012**: No client-visible response, in any tested failure condition, contains internal error
  detail, stack traces, or stored credential material.

## Out of Scope

The following Epic-01 items are deliberately excluded from this feature and belong to later slices:

- Player and Parent registration through trainer ShareLinks (US-01.02), and ShareLink generation,
  tracking, and expiry of any kind.
- Parent-created child profiles, parent/child relationships, and child login constraints
  (US-01.03, US-01.04, US-01.06).
- Child purchase approval workflows (US-01.05).
- Super Admin impersonation of other users and its audit log (US-01.07).
- Trainer invitation of coaches and the single-trainer coach assignment rule (US-01.08).
- Player and coach availability, "Best Times", and availability conflict overrides
  (US-01.09, US-01.10).
- Trainer portal branding — logo upload and colour selection (US-01.14).
- Multi-trainer player associations and the separated per-trainer views they imply.
- Camp-to-user conversion from Epic-08.
- Self-service password reset for a person who has forgotten an established password, and standalone
  email-address verification. Only the invitation-driven first-password flow that US-01.01 requires
  is in scope.
- Trainer-scoped management of their own organization's users; in this feature, directory management
  is a Super Admin capability only.
- Everything listed as Post-MVP in Epic-01 section 4, including social sign-in, two-factor
  authentication, per-user permission customization, custom roles, and bulk import or export.

## Assumptions

- **Session lifetime**: Epic-01 question Q-01.07 is unresolved, so sessions are assumed to expire
  after 7 days of inactivity, a common default for a business web application. This is a
  configurable value, not a structural decision.
- **Email verification**: Epic-01 question Q-01.05 is unresolved. Because every account in this
  feature is created by a Super Admin and activated through a link sent to the address itself,
  successfully following that link is treated as proof of control of the address, and no separate
  verification step is specified. Standalone verification is deferred with the registration flows
  that need it.
- **Setup link lifetime**: The invitation setup link is assumed to expire after 24 hours, matching
  the email-verification expiry stated in Epic-01's business rules.
- **Password rules**: Epic-01 requires only "securely hashed" and does not state strength rules; a
  12-character minimum with a breached-password check is assumed as the current common standard.
- **Photo limits**: Epic-01 does not state photo constraints; common web image formats up to 5 MB
  are assumed, with a smaller version generated for list display.
- **Placeholder email on erasure**: The anonymized address follows the pattern Epic-01 gives —
  `deleted_[account id]@example.com` — chosen because it can never receive mail.
- **Reason for erasure**: Epic-01 requires the reason to be logged, so this feature assumes the
  reason is captured from the acting Super Admin at the moment of erasure rather than reconstructed
  afterwards.
- **Original email retention on erasure**: Epic-01's data requirements call for retaining the
  original email for legal compliance. This feature assumes that record is kept in a
  Super-Admin-only compliance store and is not reachable through ordinary account views, and that
  this retention is lawful under the operator's own legal basis. Confirm with counsel before launch,
  since it is in tension with a strict interpretation of a right-to-erasure request.
- **Roles present for testing**: Coach and Player/Parent accounts must exist to prove US-01.11
  through US-01.13 across all four roles, even though their real onboarding paths are out of scope.
  FR-030 resolves this by letting a Super Admin create an account in any role; such accounts carry no
  trainer relationship until the ShareLink flows arrive.
- **Email delivery**: A transactional email service is available to deliver invitations; its
  selection and configuration are implementation concerns. Non-delivery is assumed to be visible to
  the Super Admin so a fresh invitation can be issued.
- **File storage**: Durable storage for profile photos is available, as Epic-01's external
  dependencies state.
- **Single deployment, no tenancy split yet**: All accounts live in one platform-wide directory. The
  trainer-level data isolation Epic-01 describes becomes enforceable when trainer-owned data appears
  in later epics; this feature only establishes the roles that isolation will be based on.
- **Audit retention**: Audit entries and compliance records are retained indefinitely; no purge
  policy is specified in this feature.
