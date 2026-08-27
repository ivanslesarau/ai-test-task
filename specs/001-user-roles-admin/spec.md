# Feature Specification: User Roles, Super Admin Management, ShareLink Onboarding & Portal Branding

**Feature Branch**: `001-user-roles-admin`

**Created**: 2026-08-19

**Status**: Draft — extended 2026-08-26 with player ShareLink onboarding (US-01.02),
multi-trainer association, and trainer portal branding (US-01.14)

**Input**: User description: "Read file Task/Epics/Epic-01_User_Management_Authentication_SPEC.md. Create specification (spec.md) only for initial Database structure (4 roles), authorizations and Super Admin functionality (US-01.01, US-01.11, US-01.12, US-01.13). Ignore other user stories for now."

**Input (2026-08-26 extension)**: User description: "Update spec.md. Add the implementation of
the ShareLink system for inviting players (US-01.02), if it not implemented, and the coach
portal customization (US-01.14) from the Task/Epics/Epic-01_User_Management_Authentication_SPEC.md
file. Note that a single player can be associated with multiple coaches (Multi-Trainer
Association)."

**Source Epic**: Epic-01 — User Management & Authentication. This specification covers the
foundational account structure, sign-in and permission enforcement, plus epic stories US-01.01,
US-01.11, US-01.12, US-01.13, US-01.02, and US-01.14. The remaining Epic-01 stories are
explicitly out of scope (see Out of Scope).

**Scope note on the 2026-08-26 extension**: Stories 1 to 5 and requirements FR-001 to FR-064 are
unchanged and already implemented. Stories 6 to 8 and requirements FR-065 to FR-104 are the newly
specified slice: the ShareLink invitation system players join through (US-01.02), the
multi-trainer association and separated per-trainer views that story requires, and trainer
portal branding (US-01.14). Branding is owned by a Trainer and *seen* by that trainer's coaches
and players — the epic assigns the customization itself to the Trainer role, so that is what is
specified here; coaches consume the branding but cannot change it.

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

### User Story 6 - A Player or Parent Joins a Trainer Through an Invitation Link (Priority: P1)

A trainer hands out a single durable invitation link — printed on a flyer, pasted into a message,
posted on social media. Anyone who opens it lands on a join page that names the trainer they are
about to join. Someone without an account registers right there: their own name, email address,
password and phone number, plus the name, age and gender of the player who will train. The moment
registration completes they are signed in, connected to that trainer, and looking at that trainer's
area; the trainer sees them on their roster; a confirmation email arrives.

**Why this priority**: This is the only way a player or parent can reach the platform on their own.
Until it exists, every player account has to be hand-created by a Super Admin, which is not how the
business acquires players. It is the entry point that every player-facing epic depends on.

**Independent Test**: Create a trainer, take their invitation link, open it in a browser with no
session, register, and confirm that the new person can sign in and see that trainer's area while the
trainer sees the new player on their roster. This delivers self-service player onboarding on its
own, with no other new story shipped.

**Acceptance Scenarios**:

1. **Given** a Trainer whose invitation link is active, **When** a visitor with no session opens it,
   **Then** they see a join page naming that trainer and showing that trainer's branding, offering
   both registration and sign-in.
2. **Given** the join page, **When** the visitor submits valid account and player detail, **Then**
   an Active account with the Player/Parent role is created together with its profile and player
   detail, and an association to that trainer is recorded naming the link that produced it and the
   time it happened.
3. **Given** registration has just completed, **When** the person is returned to the platform,
   **Then** they are already signed in, their landing area is that trainer's context, and a
   confirmation email naming the trainer has been sent to the address they registered with.
4. **Given** the submitted email already belongs to any account, **When** registration is submitted,
   **Then** it is refused with an invitation to sign in and follow the link again, and no second
   account exists.
5. **Given** an invitation code that has been revoked, has expired, has no owner, or whose trainer is
   not Active, **When** it is opened, **Then** a plain message says the link is no longer valid, no
   registration form is offered, and the trainer is not identified.
6. **Given** the registration form, **When** a required field is missing or the player's age falls
   outside the permitted range, **Then** the message appears beside the offending field on submit
   and nothing is stored.
7. **Given** a registration that fails partway, **When** the person retries with corrected detail,
   **Then** no half-made account, profile, or association from the first attempt is left behind.

---

### User Story 7 - A Player Trains With Several Trainers and Switches Between Them (Priority: P2)

A player or parent already using the platform is handed a second trainer's invitation link. Opening
it while signed in connects them to that trainer immediately — no second account, no second
password, no re-registration. From then on their navigation carries a trainer switcher, and each
trainer is a world of its own: whatever the platform shows them belongs to the trainer they are
currently in, and nothing is ever mixed together. The trainer they last used is the one waiting for
them the next time they sign in.

**Why this priority**: Multi-trainer membership is the shape of the business — a family trains with
a basketball academy and a strength coach — and it has to be settled in the data before any
trainer-owned data (events, tokens, content) is built on top of it. It follows Story 6 only because
a person must be able to join one trainer before they can join two.

**Independent Test**: Associate one player account with two trainers, then confirm that exactly one
account exists, that both trainers appear in the switcher, that every view shows only the active
trainer's data, and that the chosen trainer survives signing out and back in.

**Acceptance Scenarios**:

1. **Given** a signed-in Player/Parent already associated with Trainer A, **When** they open Trainer
   B's invitation link, **Then** a second association is recorded, no new account is created, they
   are told they have joined Trainer B, and their active context becomes Trainer B.
2. **Given** a player already associated with a trainer, **When** they open that trainer's link
   again, **Then** they are told they are already connected, no duplicate association is recorded,
   and the link's usage count does not rise.
3. **Given** a player associated with two trainers, **When** they sign in, **Then** the trainer they
   were last using is the active context and the switcher lists both trainers.
4. **Given** an active context of Trainer A, **When** the player switches to Trainer B, **Then**
   every view they can reach shows Trainer B's data only, no view anywhere combines the two, and
   nothing belonging to Trainer A remains on screen.
5. **Given** a player associated with exactly one trainer, **When** they sign in, **Then** no
   switcher is offered and they land in that trainer's context.
6. **Given** a player whose active trainer's account is deactivated, **When** they next open the
   platform, **Then** that trainer is gone from the switcher, they are moved to another trainer they
   still belong to, and if none remain they are told they are not currently connected to any trainer.
7. **Given** a Trainer viewing their own roster, **When** one of their players also trains with
   another trainer, **Then** nothing in any view available to that trainer reveals the other
   trainer's existence or that player's activity elsewhere.
8. **Given** a signed-in Super Admin, Trainer, or Coach, **When** they open a player invitation
   link, **Then** the platform explains that only players and parents can join through it and
   records no association.

---

### User Story 8 - A Trainer Puts Their Own Brand on Their Portal (Priority: P3)

A trainer opens their portal settings, uploads their logo, picks the primary colour of their brand,
sees both applied in a preview before committing, and saves. From that moment their own views, their
coaches' views, and the views of every player and parent while inside that trainer's context carry
that logo and that colour. A reset puts the platform's default back.

**Why this priority**: Branding changes how the product looks but not what it can do — every other
story works without it. It is nonetheless in the MVP because trainers sell their own identity to
their players, and it is the visible difference between "a platform I was told to use" and "my
academy's portal".

**Independent Test**: As a trainer, upload a logo and set a colour, then sign in as one of that
trainer's coaches and as a player associated with that trainer and confirm both see the branding,
while a player in a different trainer's context sees the platform default.

**Acceptance Scenarios**:

1. **Given** a Trainer in their branding settings, **When** they choose an image of an accepted type
   within the size limit, **Then** they see it previewed in place before saving, and only on saving
   does it appear in the header of their portal.
2. **Given** the branding settings, **When** the trainer picks a primary colour, **Then** the
   preview updates as they choose, and on saving that colour drives the accents and gradient
   everywhere in their portal.
3. **Given** saved branding, **When** the trainer chooses reset, **Then** both the logo and the
   colour return to the platform default and the stored custom values are cleared.
4. **Given** a file of an unaccepted type or one over the size limit, **When** it is chosen, **Then**
   the reason appears beside the control and the branding already in place is untouched.
5. **Given** a logo larger than the recommended display size, **When** it is saved, **Then** it is
   reduced to fit without distortion rather than refused.
6. **Given** a player associated with a branded Trainer A and an unbranded Trainer B, **When** they
   switch context, **Then** the header shows Trainer A's logo and colour in A's context and the
   platform default in B's.
7. **Given** a trainer saves a branding change, **When** one of their coaches opens their next view,
   **Then** the new branding is already showing without that coach having signed out and in again.
8. **Given** a Coach or a player, **When** they look for branding settings, **Then** the settings are
   not offered to them and a direct attempt to change another account's branding is refused.

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
- **Invitation link for an unusable trainer**: A link whose owning trainer has been deactivated or
  erased must stop admitting anyone, and must not disclose the trainer's name while refusing.
- **Wrong kind of person follows a player link**: A signed-in Super Admin, Trainer, or Coach opening
  a player invitation link must be told it is not for them; no association and no role change occurs.
- **Two registrations racing on one email**: When the same email is submitted twice at nearly the
  same moment, exactly one account results and the other attempt is refused as a duplicate.
- **The same link followed twice**: A person already connected to the trainer gains nothing and
  costs the link nothing — no second association, no extra recorded use.
- **A revoked link after the fact**: Revoking a link stops new joins but must leave every
  association it already produced fully intact.
- **Code guessing**: Invitation codes must be impractical to discover by trying values, and repeated
  invalid codes from one origin must be throttled.
- **Erased player on a roster**: A player who exercises the right to erasure must remain on each
  trainer's roster as "Deleted User" so counts stay correct, with no recoverable personal detail.
- **The active trainer disappears**: When the trainer a player is currently viewing becomes
  unavailable, the player must be moved to another trainer they belong to, or told plainly that they
  belong to none.
- **A player who belongs to no trainer**: An account can exist with zero associations — created by a
  Super Admin, or left behind when its only trainer is deactivated — and every player view must cope
  with having no context to show.
- **Cross-trainer disclosure**: Nothing a trainer can reach may reveal that one of their players
  also trains elsewhere; the isolation runs in both directions.
- **Logo replacement**: When a logo is replaced or reset, the previously stored image must not remain
  reachable, exactly as for profile photos.
- **A brand colour that hides the text**: A colour that would leave text unreadable against it must
  not produce an unreadable portal; the platform adjusts the foreground rather than accepting the
  combination as-is.
- **Uploaded artwork carrying active content**: A vector logo may contain scripts or external
  references; anything capable of executing must be stripped before the image is ever shown to
  another person.
- **Branding while signed in**: A branding change must reach people already using the portal on
  their next view, without requiring them to sign out.

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

**Input validation and optional detail**

- **FR-057**: System MUST NOT announce a field as invalid while the person is still filling in a
  form. Validation results MUST be presented when they submit it, after which the platform MAY keep
  those results up to date as the offending fields are corrected. Submitting MUST NOT be blocked in
  a way that prevents the person from discovering what is wrong.
- **FR-058**: System MUST show each rejected field's own message beside that field, whether the
  rejection was determined before the submission reached the platform or by the platform itself. A
  message naming no field MUST NOT be the only feedback given for a field-level rejection.
- **FR-059**: System MUST treat "never provided" and "cleared" as the same absent state for every
  optional detail it stores, MUST actually remove the stored value when a person clears an optional
  detail, and MUST NOT report a save as successful while retaining the previous value.

**Presentation and navigation**

- **FR-060**: System MUST display a person's stored photo wherever their photo appears, including
  their own profile, as soon as an upload succeeds.
- **FR-061**: Every view reached from another MUST offer a way back to where the person came from,
  and returning to a list MUST restore the page, search term, and filters they left it on.
- **FR-062**: Every view available to a signed-in person MUST present the same navigation frame,
  showing who is signed in, where in the platform they currently are, and a way to reach their own
  profile and to sign out. Views available before sign-in MUST NOT present it.
- **FR-063**: System MUST NOT query the user directory on each keystroke of a search term. It MUST
  wait until typing settles before searching, and MUST NOT record one reversible navigation step per
  character typed.
- **FR-105**: Every capability a person's role permits MUST be reachable through navigation or a
  control presented to them — from their role's landing area, from the navigation frame present on
  every signed-in view, or from a control on a view reached from one of those. A capability that
  exists but can be reached only by typing an address MUST be treated as not delivered. This does not
  weaken FR-015: hiding a control remains never the only barrier, and presenting one never implies
  the platform will accept the action.

**Invitation delivery**

- **FR-064**: System MUST tell the acting Super Admin when an invitation could not be delivered, on
  both first creation and re-invitation, and MUST name re-invitation as the way to try again. A
  failed delivery MUST NOT be reported as a success.

**Invitation links (ShareLinks): issuance and lifecycle**

- **FR-065**: System MUST make available to every Trainer a standing player invitation link that
  belongs to that trainer alone, never expires, and admits an unlimited number of people, so one
  link can be printed, shared, and posted without maintenance.
- **FR-066**: System MUST identify each invitation link by a code that is safe to place in a web
  address, unique across the platform, and drawn from enough randomness that valid codes cannot
  practically be found by trying values. A code MUST NOT be derivable from the owning account's
  identifier, name, or creation time.
- **FR-067**: System MUST record for each invitation link its owning trainer, who created it, its
  kind, when it was created, its expiry if it has one, its maximum number of uses if it has one, how
  many times it has been used, and whether it is currently active.
- **FR-068**: System MUST record, for every association an invitation link produces, which link
  produced it and when, and MUST increase that link's usage count by exactly one per association
  produced.
- **FR-069**: Trainers MUST be able to see their own invitation link, copy it, and replace it with a
  freshly generated one. Replacing a link MUST stop the old code admitting anyone from that moment
  and MUST leave every association the old code already produced untouched.
- **FR-070**: System MUST refuse an invitation code that is unknown, revoked, expired, exhausted, or
  whose owning trainer is not Active, stating plainly that the link is not valid, offering no
  registration form, and disclosing nothing about the trainer or about which of those reasons
  applies.
- **FR-071**: System MUST rate-limit attempts to open invitation codes per origin, so that codes
  cannot be discovered by repeated guessing.
- **FR-072**: System MUST distinguish, on every invitation link, the kind of link it is — a standing
  link that players use repeatedly, or a single-use link addressed to one named person and expiring
  on a date. Only the standing player kind is issued in this feature; the record MUST carry the
  distinction so the coach invitation flow can be added without restructuring what already exists.

**Joining a trainer through an invitation link**

- **FR-073**: System MUST show anyone opening a valid invitation link a join page that names the
  owning trainer's business and shows that trainer's branding before any personal detail is asked
  for, and MUST offer both registration and sign-in from that page.
- **FR-074**: A visitor with no session MUST be able to register from the join page by supplying the
  account holder's first name, last name, email address, password, and phone number, together with
  the player's name, age, and gender. On success the platform MUST create exactly one account with
  the Player/Parent role and status Active, exactly one profile, and exactly one player detail
  record.
- **FR-075**: System MUST apply to a password chosen during registration the same strength rules
  FR-014 states, and MUST NEVER store or transmit it in a recoverable form.
- **FR-076**: System MUST refuse registration when the submitted email address is already in use by
  any account in any status, under the same uniqueness rule as FR-004, and MUST tell the person to
  sign in and follow the link again instead.
- **FR-077**: System MUST ask, during registration, whether the person is registering themselves as
  the player or registering a player they are responsible for. When they are the player, the age
  given MUST be 18 or above; when they are registering someone they are responsible for, the age
  given MUST be between 1 and 18. Any other value MUST be refused beside the field.
- **FR-078**: System MUST, on successful registration through an invitation link, record an Active
  association between the new account and the link's owning trainer, admit the person without a
  further sign-in step, and land them in that trainer's context.
- **FR-079**: System MUST send a confirmation email naming the trainer to the address used at
  registration. A failure to deliver MUST NOT undo the registration or the association, MUST be
  recorded, and MUST NOT be reported to the person as a delivery success.
- **FR-080**: A signed-in Player/Parent who opens a valid invitation link MUST be associated with
  that trainer immediately, without registering again and without supplying any detail, and MUST be
  shown a confirmation naming the trainer they have joined.
- **FR-081**: System MUST refuse to associate an account whose role is not Player/Parent through a
  player invitation link, explaining that the link is for players and parents, and MUST change
  nothing about that account.
- **FR-082**: System MUST NOT create a second association when a person opens an invitation link for
  a trainer they are already associated with; it MUST tell them they are already connected and MUST
  NOT increase the link's usage count.
- **FR-083**: System MUST leave nothing behind when a registration through an invitation link fails
  partway — no account, no profile, no player detail, and no association may survive a failed
  attempt.

**Multi-trainer associations and separated views**

- **FR-084**: System MUST allow one Player/Parent account to hold associations with any number of
  trainers at the same time, each recorded independently with its own originating link, joining
  time, and status.
- **FR-085**: System MUST NOT create a second account for a person joining an additional trainer;
  one person has one account and one password however many trainers they train with.
- **FR-086**: System MUST maintain, for every Player/Parent holding at least one Active association,
  an active trainer context. That context MUST persist for the whole session and MUST be restored to
  the trainer last used when the person signs in again, on any device.
- **FR-087**: System MUST scope everything shown to a Player/Parent to their active trainer context
  alone, and MUST NOT offer any view that combines or totals data across two trainers.
- **FR-088**: System MUST offer a context switcher listing every trainer the person holds an Active
  association with, MUST switch the whole view on selection, and MUST NOT show the switcher when the
  person is associated with exactly one trainer.
- **FR-089**: System MUST exclude from the switcher any association that is not Active and any
  trainer whose account is not Active. When the active context becomes unavailable, the platform
  MUST move the person to another available trainer, or, if none remains, tell them plainly that
  they are not currently connected to a trainer.
- **FR-090**: System MUST show each Trainer only the players associated with that trainer, and MUST
  NOT reveal to any trainer, through any view or export available to them, that one of their players
  is also associated with another trainer.
- **FR-091**: System MUST preserve every association belonging to an erased account, showing the
  erased person on each trainer's roster as "Deleted User" under FR-045 and FR-046, so participant
  counts stay accurate.
- **FR-092**: System MUST leave the associations of a deactivated account intact and reversible, so
  reactivation restores that person's trainers exactly as they were.

**Trainer portal branding**

- **FR-093**: Trainers MUST be able to reach branding settings for their own organization. Only the
  owning trainer may change that organization's branding; Coaches and Players/Parents MUST NOT be
  offered the settings, and a request to change another organization's branding MUST be refused.
- **FR-094**: System MUST accept a portal logo supplied as a PNG, JPEG, or SVG image of at most 2 MB,
  and MUST refuse any other type or a larger file with the reason shown beside the control while the
  branding already in place stays unchanged.
- **FR-095**: System MUST remove any executable or externally-referencing content from an uploaded
  vector logo before it is stored or shown to anyone.
- **FR-096**: System MUST fit a logo larger than the recommended 200×200 display size to that size
  without distorting its proportions, rather than refusing it.
- **FR-097**: System MUST preview a chosen logo and a chosen colour in place before they are saved,
  and MUST NOT apply either to anyone until the trainer saves.
- **FR-098**: System MUST accept a primary brand colour given as a hexadecimal colour code and MUST
  use it for the portal's accent colours and gradient.
- **FR-099**: System MUST keep text and interactive elements legible against whatever primary colour
  is chosen, adjusting the foreground automatically rather than storing a combination that cannot be
  read.
- **FR-100**: Trainers MUST be able to reset branding, returning both logo and colour to the
  platform default and clearing the stored custom values.
- **FR-101**: System MUST show a trainer's branding to that trainer, to that trainer's coaches, and
  to every Player/Parent whose active trainer context is that trainer. Every other view — sign-in,
  the Super Admin's own area, and any context belonging to a different trainer — MUST show the
  platform default.
- **FR-102**: System MUST make a saved branding change visible on the next view any affected person
  opens, without requiring them to sign out and in again.
- **FR-103**: System MUST ensure that a logo replaced or reset is no longer reachable, in the same
  way FR-034 requires of replaced profile photos.
- **FR-104**: System MUST store branding per trainer as a logo reference and a primary colour, each
  of which may be absent. An absent value means the platform default and MUST be recorded as absent
  rather than as an empty value.


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
- **Invitation Link (ShareLink)**: A trainer's standing offer to join them, addressed by an
  unguessable code. Holds the owning trainer, its creator, its kind, creation time, optional expiry,
  optional maximum uses, its running usage count, and whether it is active. One trainer has one
  standing player link at a time; replacing it retires the previous code.
- **Trainer–Player Association**: The fact that one Player/Parent account trains with one Trainer.
  Holds the trainer, the player account, the invitation link that produced it, when it was formed,
  and its status. Many per player and many per trainer; the pair is unique. Survives the erasure and
  the deactivation of either side.
- **Active Trainer Context**: Which of a Player/Parent's trainers they are currently looking at.
  Exactly one per player account at a time, remembered against the account so it is the same
  wherever they sign in, and the boundary that scopes every view they see.
- **Trainer Portal Branding**: The visual identity one Trainer presents to their own organization —
  a logo reference and a primary brand colour, either of which may be absent, plus when it last
  changed. Exactly one per Trainer account; absent values mean the platform default.

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
- **SC-013**: Typing a 20-character search term into the user directory produces exactly one
  directory query and exactly one reversible navigation step, and the results reflect the whole term.
- **SC-014**: The navigation frame is present on 100% of views reachable while signed in and on 0% of
  views reachable before signing in, and returning to a filtered directory from any account opened
  from it restores that filtered view unchanged.
- **SC-015**: A person with no account can go from opening a trainer's invitation link to standing in
  that trainer's area, registered and signed in, in under 3 minutes, and appears on that trainer's
  roster immediately.
- **SC-016**: A signed-in player who opens a second trainer's invitation link is associated and
  viewing that trainer's context within 5 seconds, and exactly one account still exists for them.
- **SC-017**: Across a test set of players associated with two trainers, 100% of views show data
  belonging to the active context only, and no view returns data from the other trainer.
- **SC-018**: Switching trainer context completes within 2 seconds, and the trainer chosen is still
  the active one after signing out and signing back in on a different device.
- **SC-019**: 100% of registrations and joins made through an invitation link record which link
  produced them and raise that link's usage count by exactly one; repeat visits by an
  already-connected person raise it by zero.
- **SC-020**: A replaced invitation link stops admitting new people within 1 minute, while 100% of
  the associations it previously produced remain intact.
- **SC-021**: An automated trial of 10,000 invalid invitation codes from one origin discovers no
  valid link and is throttled after no more than 10 consecutive invalid codes.
- **SC-022**: A trainer can upload a logo and set a brand colour in under 2 minutes, and their
  coaches and players see the change within 1 minute without signing out.
- **SC-023**: 100% of accepted brand colours produce text and controls meeting a contrast ratio of at
  least 4.5:1 against the surfaces they sit on.
- **SC-024**: A player associated with one branded and one unbranded trainer sees the correct
  branding in 100% of context switches, with no flash of the other trainer's identity.
- **SC-025**: No trainer-facing view or export reveals that one of their players trains with another
  trainer, verified by a test covering every view available to a Trainer and to a Coach.
- **SC-026**: For each of the four roles, 100% of the views that role is permitted to reach are
  reachable by clicking from that role's landing area or navigation frame, and 0% require an address
  to be typed — verified per role against the application's own route table rather than a hand-kept
  list.

## Out of Scope

The following Epic-01 items are deliberately excluded from this feature and belong to later slices:

- Parent-created child profiles, parent/child relationships, and child login constraints
  (US-01.03, US-01.04, US-01.06). A registration through an invitation link therefore creates
  exactly one player, not a family.
- The family-member selection prompt US-01.02 describes for a parent joining an additional
  trainer — "who will train with this trainer?", answered against the parent and their children
  — is deferred with child profiles. Until then, joining a trainer associates the one player the
  account holds.
- Coach invitation links: the single-use, one-person, seven-day variety and the rule that a coach
  works for exactly one trainer (US-01.08). The invitation link record carries a kind so this can
  be added without restructuring, but no such link is issued here.
- Reporting and analytics over invitation link usage, including conversion and referral tracking
  (Epic-06). Usage is recorded here; only later epics read it as analytics.
- Trainer-side management of an existing association — removing a player from their roster, or a
  parent editing which trainers a family member trains with (US-01.04). Associations here are
  formed by joining and end only when an account leaves Active status.
- Branding beyond one logo and one primary colour: separate light and dark logos, font choices,
  and layout customization are Phase 2 in the epic.
- Child purchase approval workflows (US-01.05).
- Super Admin impersonation of other users and its audit log (US-01.07).
- Player and coach availability, "Best Times", and availability conflict overrides
  (US-01.09, US-01.10).
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

**Assumptions added with the 2026-08-26 extension**

- **One standing link per trainer**: Epic-01 says a trainer's player link is static, unlimited, and
  never expires, but not how many a trainer may hold. Exactly one standing link per trainer is
  assumed, replaceable when a trainer wants the old code retired. Multiple named campaign links are
  a marketing concern and belong with Epic-06.
- **What "registering a player" creates here**: US-01.02's form collects parent contact details and
  player details together. Because child profiles (US-01.03) are out of scope, a registration is
  assumed to create one account holding one player. Whether that player is the account holder or a
  dependant is captured at registration (FR-077) so the family structure can be layered on later
  without re-asking.
- **Age boundary**: Epic-01 states that everyone under 18 trains through a parent-managed account and
  that child ages run 1 to 18. It follows that a person registering themselves is 18 or over; that
  reading is assumed rather than a separate rule.
- **The confirmation email is not a verification step**: The email sent after joining confirms the
  association and names the trainer. Standalone email-address verification remains out of scope, as
  it already was, so the confirmation carries no link that must be followed.
- **Where the active trainer context lives**: It is assumed to be remembered against the account
  rather than the browser, so a family that switches devices finds the same trainer waiting. This is
  a behaviour assumption, not a storage decision.
- **"Separated views" in this slice**: Epic-01's separated-views architecture concerns calendars,
  tokens, content, and reservations, none of which exist yet. Here the requirement is established as
  a rule — every player-facing view is scoped to the active trainer and no combined view exists —
  so the epics that add that data inherit the boundary rather than retrofitting it.
- **Vector logos are accepted but sanitized**: The epic lists PNG and JPG in one place and PNG, JPG,
  and SVG in its validation rules. All three are assumed accepted, on the assumption that an SVG is
  stripped of anything executable before storage, since an uploaded vector is otherwise a way to run
  code in another person's browser.
- **Legibility outranks the chosen colour**: The epic asks for a hex colour and says nothing about
  contrast. It is assumed the platform derives readable foreground colours from whatever primary
  colour is chosen, rather than refusing colours or letting a portal become unreadable.
- **Branding audience**: The epic says branding is visible to a trainer's players, coaches, and
  parents. It is assumed that Super Admin views and pre-sign-in views keep the platform default, so
  administrators always know which platform they are on.
- **A player may belong to no trainer**: Super Admin-created Player/Parent accounts (FR-030) and
  accounts whose only trainer was deactivated hold zero associations. Such an account is assumed to
  be valid and to see an empty state rather than an error.
