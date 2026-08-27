# Feature Specification: User Roles, Super Admin Management, ShareLink Onboarding, Portal Branding & Family Accounts

**Feature Branch**: `001-user-roles-admin`

**Created**: 2026-08-19

**Status**: Draft — extended 2026-08-26 with player ShareLink onboarding (US-01.02),
multi-trainer association, and trainer portal branding (US-01.14); extended 2026-08-27 with
parent/child family accounts, constrained child sign-in, and the parent approval workflow
(US-01.03, US-01.04, US-01.05, US-01.06)

**Input**: User description: "Read file Task/Epics/Epic-01_User_Management_Authentication_SPEC.md. Create specification (spec.md) only for initial Database structure (4 roles), authorizations and Super Admin functionality (US-01.01, US-01.11, US-01.12, US-01.13). Ignore other user stories for now."

**Input (2026-08-26 extension)**: User description: "Update spec.md. Add the implementation of
the ShareLink system for inviting players (US-01.02), if it not implemented, and the coach
portal customization (US-01.14) from the Task/Epics/Epic-01_User_Management_Authentication_SPEC.md
file. Note that a single player can be associated with multiple coaches (Multi-Trainer
Association)."

**Input (2026-08-27 extension)**: User description: "Update spec.md. Add the complex Parent/Child
business logic from Task/Epics/Epic-01_User_Management_Authentication_SPEC.md (user stories
US-01.03, US-01.04, US-01.05, US-01.06). Pay special attention to the parent purchase approval
workflow (Pending Parent Approval)."

**Source Epic**: Epic-01 — User Management & Authentication. This specification covers the
foundational account structure, sign-in and permission enforcement, plus epic stories US-01.01,
US-01.11, US-01.12, US-01.13, US-01.02, US-01.14, US-01.03, US-01.04, US-01.05, and US-01.06.
The remaining Epic-01 stories are explicitly out of scope (see Out of Scope).

**Scope note on the 2026-08-26 extension**: Stories 1 to 5 and requirements FR-001 to FR-064 are
unchanged and already implemented. Stories 6 to 8 and requirements FR-065 to FR-104 are the newly
specified slice: the ShareLink invitation system players join through (US-01.02), the
multi-trainer association and separated per-trainer views that story requires, and trainer
portal branding (US-01.14). Branding is owned by a Trainer and *seen* by that trainer's coaches
and players — the epic assigns the customization itself to the Trainer role, so that is what is
specified here; coaches consume the branding but cannot change it.

**Scope note on the 2026-08-27 extension**: Stories 1 to 8 and requirements FR-001 to FR-105 are
unchanged. Stories 9 to 13 and requirements FR-106 to FR-159 are the newly specified slice: one
account holding a whole family (US-01.03), the parent's control over which trainers each child
trains with (US-01.04), a child's own constrained sign-in and the invitation link that is blocked
for them (US-01.06), and the parent approval workflow the epic calls "Pending Parent Approval"
(US-01.05).

This extension **changes a structure the earlier slices established**, and that change is
deliberate rather than incidental. Until now one Player/Parent account meant exactly one player,
and a trainer association joined an *account* to a trainer. From here an account holds one or more
**player profiles** — at most one for the account holder themselves, plus one per child — and an
association joins a *player profile* to a trainer. FR-114 states the refinement and names every
earlier requirement whose subject moves from the account to the profile; nothing that was
previously true of a single-player account stops being true, because such an account becomes an
account holding exactly one profile.

The purchase approval workflow is specified once, as a **generic child-initiated request** that a
parent resolves, because the epic applies the identical mechanism to three different subjects: a
USD payment, a token spend, and — through US-01.06's blocked invitation link — a child asking to
join a trainer. Only the last of those three has a subject that exists in the platform today;
events, payments, and tokens arrive with Epic-02 and Epic-05. So the mechanism ships complete and
demonstrable now, driven by join requests, and the payment and token kinds are specified as rules
and recorded data whose *execution* defers to Epic-05 (FR-142, FR-158). This is what keeps the
headline workflow testable in this slice instead of being a schema waiting for another epic.

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

### User Story 9 - A Parent Puts Their Whole Family on One Account (Priority: P1)

A parent already using the platform opens their family page and adds a child: the child's name, age
and gender, optionally a school and a photo. Because the account holder may train themselves as
well, each player on the account is marked either as the account holder or as a child. As the child
is created the platform asks, in the plainest way the situation allows, whether the child will train
with the trainers the parent already trains with — a single yes-or-no question when there is only
one trainer, a checklist when there are several, and nothing at all when there are none. From then
on the parent's navigation carries every player on the account, and each child is a world of their
own: their own trainers, their own calendar, their own attendance.

**Why this priority**: Every remaining story in this extension needs a child to exist before it has
a subject. It is also the story that changes the shape of the data — one account, many players —
so shipping it first means the association and approval work is built on the final structure
instead of migrating onto it later.

**Independent Test**: Sign in as a parent associated with one trainer, add two children answering
yes for one and no for the other, and confirm both profiles exist under the one account, that only
the first is on the trainer's roster, and that the parent's navigation now offers a choice between
themselves and each child. This delivers family accounts on its own with no other new story
shipped.

**Acceptance Scenarios**:

1. **Given** a signed-in Player/Parent, **When** they add a child with a name, age and gender,
   **Then** a player profile marked as a child is created under their account and appears in their
   family list.
2. **Given** a parent associated with exactly one trainer, **When** they add a child, **Then** they
   are asked a single question naming that trainer, and answering yes associates the child with it
   while answering no leaves the child with no trainer.
3. **Given** a parent associated with several trainers, **When** they add a child, **Then** they are
   offered the list of those trainers and only the ones they select are associated with the child.
4. **Given** a parent associated with no trainer, **When** they add a child, **Then** no trainer
   question is asked and the child profile is created with no association.
5. **Given** an age outside 1 to 18 for a child, or a missing name or gender, **When** the form is
   submitted, **Then** the message appears beside the offending field and no profile is created.
6. **Given** the account already holds a child of a very similar name and the same age, **When**
   another is submitted, **Then** the parent is warned that it may be a duplicate and may either
   confirm or go back, and confirming creates the profile.
7. **Given** a parent who trains themselves, **When** they look at their family list, **Then** their
   own player profile appears alongside their children's, distinguished as the account holder.
8. **Given** a parent, **When** they attempt to add a player marked as the account holder while one
   already exists, **Then** the attempt is refused, because an account has at most one of those.
9. **Given** a parent, **When** they attempt to create a child profile whose age is 18 or above,
   **Then** the attempt is refused with an explanation that adults hold their own accounts.
10. **Given** a signed-in Trainer, Coach, or Super Admin, **When** they attempt to add a child
    profile to a Player/Parent account, **Then** the attempt is refused — only the account holder
    manages their own family.
11. **Given** a parent, **When** they open or edit a player profile belonging to a different
    account, **Then** the attempt is refused unless they are a Super Admin.

---

### User Story 10 - A Parent Decides Which Trainers Each Child Trains With (Priority: P1)

A parent opens their family page and sees, for every player on the account, which trainers that
player trains with and since when. They can add a trainer to a child either by following that
trainer's invitation link or by picking from the trainers they themselves already train with — the
second being the common case, since families usually add a sibling to the program they already
know. They can also take a child out of a program: the platform states plainly that upcoming
reservations will be cancelled, and once confirmed the child is off that trainer's roster while
everything that already happened stays on the record.

**Why this priority**: A family's membership changes constantly — a sibling joins, a season ends,
a child switches sports. Without this the only way to change a child's trainers would be to create
the profile again, and the trainer's roster would drift out of step with reality. It sits with
Story 9 at P1 because a child profile that cannot be re-pointed is barely usable.

**Independent Test**: With a parent who trains with two trainers and has one child on one of them,
add the second trainer to the child by picking from the parent's own trainers, confirm the child
appears on both rosters, then remove one and confirm the child leaves that roster while the past
record survives and the other association is untouched.

**Acceptance Scenarios**:

1. **Given** a signed-in parent on their family page, **When** they look at a child, **Then** they
   see that child's name, age and every trainer the child is associated with together with the date
   each association began.
2. **Given** a parent viewing a child, **When** they choose to add a trainer and pick one of the
   trainers they themselves already train with, **Then** the child is associated with that trainer
   and appears on that trainer's roster.
3. **Given** a parent viewing a child, **When** they choose to add a trainer by supplying an
   invitation link, **Then** a valid link associates that child with its owning trainer, and an
   invalid one is refused under the same rules as any other use of that link.
4. **Given** a child already associated with a trainer, **When** the parent adds the same trainer
   again, **Then** they are told the child is already connected and no second association is
   recorded.
5. **Given** a parent viewing a child's association, **When** they choose to remove it, **Then**
   they must confirm through a prompt naming the child and the trainer and stating that upcoming
   reservations with that trainer will be cancelled.
6. **Given** the removal is confirmed, **When** it completes, **Then** the association becomes
   inactive, the trainer's roster no longer lists the child, and the record of what the child
   already did with that trainer remains intact.
7. **Given** a child whose association with a trainer was removed, **When** the parent later adds
   that trainer again, **Then** the same child profile is reused, no duplicate profile is created,
   and the earlier history remains attached.
8. **Given** a parent removing a child's last remaining association, **When** it completes,
   **Then** the child profile still exists with no trainer and is shown as belonging to no program.
9. **Given** a child with their own sign-in, **When** they attempt to add or remove any trainer for
   themselves, **Then** the attempt is refused whether it is made through the interface or directly.
10. **Given** a parent, **When** they attempt to change the associations of a player profile on
    another account, **Then** the attempt is refused.

---

### User Story 11 - A Child Signs In and Finds Most Doors Locked (Priority: P2)

A parent can give a child their own way in, by supplying an email address for that child; the child
then chooses their own password and signs in to a portal of their own. What they find is deliberately
narrow. They can look at their program, see what they are booked into, see their own progress, see
how many tokens they have, change their photo, and move between their own trainers if they have more
than one. What they cannot do is anything that costs money, changes who they train with, or reaches
into the rest of the family: their parent's training and their siblings' training are invisible to
them. When a child follows a new trainer's invitation link the platform stops them, tells them to
ask their parent, and emails the parent the link — so the child's enthusiasm reaches the parent
instead of quietly enlarging the family's commitments.

**Why this priority**: Children being able to look at their own training without being able to spend
or commit is what makes the family model safe enough to hand to a child at all. It follows Stories 9
and 10 because a child needs a profile and trainers before there is anything for them to sign in to.

**Independent Test**: Give a child their own sign-in, sign in as that child, and confirm the
permitted views work while every forbidden action is refused — including when the request is made
directly rather than through the interface. Then, as the child, follow a third trainer's invitation
link and confirm no association is created and the parent receives the email.

**Acceptance Scenarios**:

1. **Given** a parent viewing one of their children, **When** they supply an email address for that
   child and grant them a sign-in, **Then** a Player/Parent account is created for the child, linked
   to the parent, and the child is invited to choose their own password through the same setup-link
   flow any invited account uses.
2. **Given** an email address already belonging to any account, **When** the parent supplies it for
   a child, **Then** it is refused as a duplicate under the existing uniqueness rule and no child
   sign-in is created.
3. **Given** a child who has set their password, **When** they sign in, **Then** they land in their
   own area showing only their own player profile and their own trainers.
4. **Given** a signed-in child, **When** they browse their program, view what they are booked into,
   view their own progress, view their token balance, or change their own photo and preferences,
   **Then** each of those succeeds.
5. **Given** a signed-in child, **When** they attempt to add or remove a trainer, change a payment
   method, buy tokens, complete a purchase, delete their account, or change any setting belonging to
   the parent, **Then** each attempt is refused, whether made through the interface or by addressing
   the platform directly.
6. **Given** a signed-in child, **When** they attempt to reach their parent's training or a sibling's
   training, **Then** the attempt is refused and nothing about it is disclosed to them.
7. **Given** a child associated with several trainers, **When** they sign in, **Then** a switcher
   lists their own trainers only, with no grouping for the account holder and no sibling anywhere in
   it.
8. **Given** a child associated with exactly one trainer, **When** they sign in, **Then** no switcher
   is offered.
9. **Given** a signed-in child, **When** they open a valid trainer invitation link, **Then** no
   association is created, they are told to ask their parent to register them with that trainer, and
   nothing about their account changes.
10. **Given** a child has followed a new trainer's link, **When** the block takes effect, **Then**
    an email reaches the parent naming the child and the trainer, carrying the link and a way to
    review the request.
11. **Given** a child who follows the link of a trainer they already train with, **When** the block
    would apply, **Then** they are simply told they are already connected and the parent is not
    emailed.
12. **Given** a parent, **When** they revoke a child's sign-in, **Then** the child can no longer sign
    in, any session they held stops working immediately, and the child's profile, trainers and
    history are all untouched.
13. **Given** a child account, **When** anything about it is emailed other than its own password
    setup or reset, **Then** that email goes to the parent's address rather than the child's.

---

### User Story 12 - A Parent Approves or Denies What Their Child Asks For (Priority: P2)

Whenever a child asks for something that costs money or changes who they train with, the request
stops and waits. The child sees it sitting at **Pending Parent Approval**; the parent gets an email
and an in-app notice naming the child, what is being asked, and the amount if there is one. From
their pending list the parent can approve it — at which point the platform carries the action out
exactly as if the parent had done it themselves — deny it, or ask the child for more information
before deciding. Any of the three can carry a note. Nothing happens on its own except the clock: a
request left untouched for 48 hours expires, which denies it, and both the parent and the child are
told. USD payments always come through here and no setting can turn that off. Token spending comes
through here too by default, though a parent may decide, child by child, that a particular child can
spend tokens without asking.

**Why this priority**: This is the mechanism that makes a child's sign-in trustworthy, and the epic's
central family rule. It is P2 rather than P1 because a child must be able to sign in and ask for
something before there is a request to approve — but it is the story this extension exists to
deliver.

**Independent Test**: As a child, follow a new trainer's invitation link to raise a join request.
Sign in as the parent, find it in the pending list, and approve it — confirm the child is now
associated with that trainer and sees the status change. Repeat with a denial, and repeat a third
time letting the clock run past 48 hours, confirming the request expires as denied and the child is
never associated. This exercises the whole workflow end to end without any payment existing.

**Acceptance Scenarios**:

1. **Given** a child raises a request that needs approval, **When** it is created, **Then** its
   status reads Pending Parent Approval, the child can see it and its status, and the requested
   action has not been carried out.
2. **Given** a request has just been created, **When** the parent is notified, **Then** both an email
   and an in-app notice reach them naming the child, what is requested, and the amount and currency
   when there is one.
3. **Given** a parent with pending requests, **When** they open their pending list, **Then** each
   entry shows the child, what is asked, the amount if any, when it was requested, and how long
   remains before it expires.
4. **Given** a pending request, **When** the parent approves it, **Then** the requested action is
   carried out under exactly the rules that would apply had the parent performed it, the status
   becomes approved, and the child sees the status change.
5. **Given** a pending request, **When** the parent denies it, **Then** the action is not carried
   out, the status becomes denied, and the child is told, together with the parent's note if one was
   given.
6. **Given** a pending request, **When** the parent asks for more information and adds a note,
   **Then** the child is shown that note and can reply, which returns the request to pending without
   restarting its expiry.
7. **Given** a request that has been pending for 48 hours with no decision, **When** the deadline
   passes, **Then** the request expires as a denial, the action is not carried out, and both the
   parent and the child are notified.
8. **Given** an approval whose action cannot be carried out — the trainer's link has since been
   revoked, or the child was meanwhile removed — **When** the parent approves, **Then** they are told
   why it could not be completed and the request is not left recorded as approved-but-undone.
9. **Given** a child with a pending request, **When** they attempt to approve it themselves or to
   carry out the underlying action directly, **Then** the attempt is refused.
10. **Given** a child with a pending request, **When** they withdraw it, **Then** it closes as
    withdrawn, the action is not carried out, and the parent's pending list no longer offers it.
11. **Given** a parent, **When** they attempt to resolve a request belonging to a child on another
    account, **Then** the attempt is refused.
12. **Given** a child who has already raised a request for something, **When** they raise the same
    request again while the first is still pending, **Then** no second request is created and they
    are shown the one already waiting.
13. **Given** a request for a USD payment and a parent who has switched on unsupervised token
    spending for that child, **When** the child requests the USD payment, **Then** it still requires
    approval, because no setting can waive that.
14. **Given** a child whose parent has left unsupervised token spending off, **When** the child
    spends tokens, **Then** the spend waits for approval exactly as a payment does.
15. **Given** a child whose parent has switched unsupervised token spending on, **When** the child
    spends tokens, **Then** the spend completes immediately and the parent receives a notice that
    tells them what happened without asking them to decide anything.
16. **Given** a parent who changes the token setting for one child, **When** they look at their other
    children, **Then** those children's settings are unchanged, and any request already pending is
    unaffected by the change.
17. **Given** a resolved request, **When** the audit trail is reviewed, **Then** it records the child,
    the request, the decision, who made it, any note, and when.
18. **Given** a parent account that is no longer active, **When** one of its pending requests is
    reached, **Then** it cannot be approved by anyone, is never approved automatically, and expires
    on its original schedule.

---

### User Story 13 - A Family Chooses Who Joins When a Parent Follows a New Trainer's Link (Priority: P3)

A parent who already has children on the account follows a new trainer's invitation link. Rather
than silently joining the parent alone — or, worse, the whole family — the platform asks who this is
for: the account holder, any of the children, or several of them at once. Only the players ticked
are associated with the new trainer.

**Why this priority**: Without it a parent can still reach the same outcome, by joining themselves
and then adding each child from the family page (Story 10). This story removes that detour at the
moment the family is most likely to want it, which makes it a refinement rather than a capability.

**Independent Test**: As a parent with two children, follow a third trainer's invitation link,
select the account holder and one child, and confirm exactly those two are on the new trainer's
roster while the other child is not.

**Acceptance Scenarios**:

1. **Given** a signed-in parent with at least one child, **When** they open a valid invitation link
   for a trainer none of them train with, **Then** they are asked who will train with that trainer
   and offered the account holder, if they hold a player profile, plus every child on the account.
2. **Given** that question, **When** the parent selects one or more players and confirms, **Then**
   exactly those players are associated with the trainer and no other player on the account is.
3. **Given** that question, **When** the parent selects nobody and confirms, **Then** no association
   is created and they are returned where they came from with nothing changed.
4. **Given** a parent whose account holds no child profiles, **When** they open a new trainer's link,
   **Then** no question is asked and they are associated exactly as Story 7 describes.
5. **Given** some players on the account already train with that trainer, **When** the question is
   shown, **Then** those players are shown as already connected and cannot be selected again, and
   the link's usage count rises only by the number of new associations actually created.
6. **Given** the parent selects several players, **When** the associations are created, **Then** the
   parent's active context moves to the new trainer, using the account holder's profile if it was
   selected and otherwise the first selected child.

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
- **A child turning 18**: A child profile whose age crosses 18 must not silently become invalid or
  lock the family out of it. The profile stays valid and parent-managed; moving that person onto an
  account of their own is not specified here and must not be attempted implicitly.
- **The parent's account is deactivated**: Deactivating a parent must not leave children able to
  spend or commit unsupervised. Every child sign-in on that account stops working too, and pending
  requests become unresolvable rather than approving themselves.
- **The parent's account is erased**: A privacy erasure against a parent must not orphan a child
  profile that other people's records point at. Children remain on trainers' rosters as "Deleted
  User" exactly as the parent does, and nothing recoverable about either survives.
- **A child sign-in outliving its profile**: When a child profile is removed, any sign-in granted to
  that child must stop working; a credential must never outlive the player it belongs to.
- **The same email for parent and child**: A parent supplying their own address as the child's
  sign-in must be refused by the existing uniqueness rule, not accepted as a shared login.
- **A child with no trainer at all**: A child created without a trainer, or whose only association
  was removed, must see an empty state explaining they are not in a program, never an error.
- **Two parents, one child**: Only the account that owns a child profile can manage it. A second
  adult managing the same child is not specified here and must not be inferred from a shared email
  or surname.
- **A trainer removed while a join request is pending**: A pending request whose trainer has been
  deactivated, or whose invitation link has been revoked, must fail cleanly on approval and say why,
  rather than creating an association to something unusable.
- **Approving twice**: A request resolved once must not be resolvable again, including when two
  parent sessions approve the same request at nearly the same moment — one decision wins and the
  other is told the request already closed.
- **Expiry racing a decision**: A request reaching 48 hours at the same moment the parent approves it
  must resolve exactly once, and the action must be carried out either fully or not at all.
- **A price that moves between request and approval**: Approving must never charge an amount the
  parent was not shown. If the underlying amount has changed, the request fails rather than
  proceeding at the new figure.
- **The token setting flipped mid-flight**: Switching unsupervised token spending on must not
  auto-approve requests already waiting, and switching it off must not retroactively undo spends
  already completed.
- **A child requesting the same thing repeatedly**: Repeated identical requests must collapse onto
  the one already pending rather than filling the parent's list with duplicates.
- **A sibling's data through a shared account**: A child signed in must not reach a sibling's
  training even though both profiles sit on one account — the isolation between siblings is as strict
  as the isolation between trainers.
- **A trainer seeing the rest of the family**: A trainer associated with one child must see that
  child and the responsible parent's contact details, and must not learn of siblings on the same
  account who do not train with them.
- **Notification storms**: A parent with many children must not receive one email per child for the
  same event, and a child repeatedly following the same blocked link must not generate an email each
  time.

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

**Player profiles: one account, a whole family (US-01.03)**

- **FR-106**: System MUST allow one Player/Parent account to own one or more player profiles, and
  MUST distinguish each profile as either the account holder's own or a child's. An account MUST hold
  at most one profile of the account holder's own kind and any number of children's.
- **FR-107**: System MUST store on every player profile a first and last name, an age, and a gender,
  all required, plus optionally a school, a photo reference, and a jersey number. The
  trainer-assigned skill level FR-007 defines MUST be held per profile and MUST remain uneditable by
  the family.
- **FR-108**: System MUST require the age on a profile of the account holder's own kind to be 18 or
  above, and the age on a child's profile to be between 1 and 18, refusing any other value beside the
  offending field. This is the same boundary FR-077 applies at registration.
- **FR-109**: System MUST allow only a Player/Parent account to own player profiles, and MUST treat
  an account holding a profile of the account holder's own kind as a player in every respect — the
  parent trains alongside their children rather than merely administering them.
- **FR-110**: System MUST warn a parent, before creating a child profile, when the account already
  holds a child of a closely similar name and the same age, and MUST allow the parent to proceed
  anyway. The warning MUST NOT block creation.
- **FR-111**: Parents MUST be able to edit and to remove any player profile their account owns.
  Removal MUST preserve every historical record attached to that profile, in the same way FR-038 and
  FR-039 preserve the history of a deactivated account.
- **FR-112**: System MUST refuse any attempt to read, edit, or remove a player profile the requester's
  account does not own, unless the requester is a Super Admin. No Trainer, Coach, or other family may
  create, edit, or remove a profile on someone else's account.
- **FR-113**: System MUST hold the family's contact details — phone number and emergency contact —
  against the parent account rather than per child, so a child profile carries no contact information
  of its own.

**Associations move from the account to the player profile (refines FR-084 to FR-092)**

- **FR-114**: System MUST record every trainer association between one **player profile** and one
  Trainer, replacing the account-level association the earlier slices defined. Every requirement that
  previously spoke of associating an account — FR-078, FR-080, FR-082, FR-084, FR-085, FR-086,
  FR-087, FR-088, FR-089, FR-090, FR-091, FR-092 — MUST be read with the player profile as its
  subject. An account that holds exactly one profile MUST behave exactly as it did before this
  change.
- **FR-115**: System MUST keep each profile's associations wholly independent of every other profile
  on the same account, including their originating invitation link, joining time, and status, so a
  parent and each child may train with entirely different trainers.
- **FR-116**: System MUST show a Trainer only the player profiles associated with that trainer,
  together with the contact details of the account responsible for each, and MUST NOT reveal to that
  trainer any other profile on the same account.
- **FR-117**: System MUST define the active context of a signed-in family member as one pair of a
  player profile and a trainer, and MUST scope every view they can reach to that pair alone. No view
  MUST combine or total data across two profiles or across two trainers.
- **FR-118**: System MUST present a parent a context switcher that groups their own player profile's
  trainers separately from their children's, naming the child on every entry, and MUST NOT present a
  switcher when the account has exactly one profile-and-trainer pair in total.
- **FR-119**: System MUST present a signed-in child a context switcher listing only their own
  trainers, with no grouping for the account holder and no sibling present in it, and MUST NOT
  present one when the child has exactly one trainer.
- **FR-120**: System MUST restore, when a family member signs in, the profile-and-trainer pair they
  last used, and MUST fall back to another available pair — or to a plain statement that they are
  connected to no trainer — when that pair is no longer available, extending FR-089 to the family
  structure.
- **FR-121**: System MUST hold the training data that later epics attach to a player — calendar,
  reservations, attendance, availability, tokens, content — per player profile per trainer, so that
  the separation this feature establishes is inherited rather than retrofitted.

**Choosing a child's trainers when the profile is created (US-01.03)**

- **FR-122**: System MUST, while a parent is creating a child profile, ask which trainers the child
  will train with, presenting a single question naming the trainer when the parent is associated with
  exactly one, a selection list when the parent is associated with several, and no question at all
  when the parent is associated with none.
- **FR-123**: System MUST associate a newly created child only with the trainers the parent
  explicitly chose, and MUST create the profile with no association at all when the parent chose
  none. An association MUST NEVER be inferred from the parent's own associations without the parent
  saying so.

**A parent manages each child's trainers (US-01.04)**

- **FR-124**: Parents MUST be able to see, for every player profile on their account, that player's
  name and age and every trainer they are associated with together with the date each association
  began.
- **FR-125**: Parents MUST be able to add a trainer to any player profile on their account in two
  ways: by supplying that trainer's invitation link, which is validated under FR-070 exactly as any
  other use of it, or by selecting from the trainers the parent's account is already associated with.
- **FR-126**: Parents MUST confirm the removal of an association through a prompt naming the player
  and the trainer and stating that upcoming reservations with that trainer will be cancelled. On
  confirmation the association MUST become inactive, the trainer's roster MUST no longer list that
  player, and every historical record of what happened under it MUST remain intact.
- **FR-127**: System MUST reuse the same player profile when a previously removed trainer is added
  again, MUST NOT create a duplicate profile, and MUST leave the earlier history attached to it.
- **FR-128**: System MUST restrict the addition and removal of a player profile's associations to the
  account that owns the profile, and to Super Admins; a signed-in child MUST NOT be able to change
  any association, including their own.

**A child's own sign-in (US-01.06)**

- **FR-129**: Parents MUST be able to grant a child their own sign-in by supplying an email address
  for that child. The platform MUST create a Player/Parent account holding that address, linked to
  the parent's account and to that child's profile, subject to the email uniqueness rule FR-004
  states, and MUST invite the child to set their own password through the setup-link flow FR-025 to
  FR-027 define.
- **FR-130**: System MUST send every notification concerning a child — approval requests, decisions,
  reservations, financial notices — to the parent's email address. A child's own address MUST receive
  nothing but the credential mail for that child's own account: the setup link FR-129 requires, and
  any password reset for it once self-service reset exists.
- **FR-131**: A signed-in child MUST be able to browse the events their trainers offer without
  committing to them, view content already available to them, view their own progress, view their own
  token balance without spending it, update their own photo and preferences, move between their own
  trainer contexts, and raise a request for their parent to approve.
- **FR-132**: System MUST refuse a signed-in child every one of the following: joining a new trainer,
  changing any trainer association, adding or removing a payment method, purchasing tokens,
  completing any purchase without an approval, deleting their own account, owning a child profile of
  their own, reading or changing anything belonging to the parent or to a sibling, and changing any
  setting the parent owns — including the setting that governs their own token spending.
- **FR-133**: System MUST enforce every restriction in FR-132 when the request is received, not only
  by withholding a control, exactly as FR-015 requires.
- **FR-134**: Parents MUST be able to revoke a child's sign-in at any time. Revocation MUST end every
  session that child holds immediately, under FR-012, and MUST leave the child's profile,
  associations, and history untouched.
- **FR-135**: System MUST end a child's sign-in when that child's profile is removed, so no credential
  outlives the player it belongs to; and MUST NOT allow a child account to convert itself into an
  independent account.
- **FR-136**: System MUST stop every child sign-in on an account whose parent has left Active status,
  and MUST restore them when the parent is reactivated, so a child can never act while the
  responsible adult cannot.

**A child follows a trainer's invitation link (US-01.06)**

- **FR-137**: System MUST refuse to associate a signed-in child through a trainer invitation link.
  It MUST tell the child to ask their parent to register them with that trainer, and MUST change
  nothing about the child's account, profile, or associations.
- **FR-138**: System MUST, when it blocks a child in this way, raise an approval request of the
  join-a-trainer kind against the responsible parent and MUST email that parent, naming the child and
  the trainer, carrying the invitation link and a way to review the request.
- **FR-139**: System MUST NOT raise a second request when one for the same child and the same trainer
  is already pending; it MUST surface the pending one instead, and MUST NOT email the parent again.
- **FR-140**: System MUST tell a child who follows the link of a trainer they already train with that
  they are already connected, and MUST raise no request and send no email.

**Approval requests: the Pending Parent Approval workflow (US-01.05)**

- **FR-141**: System MUST record every approval request with the child profile it concerns, the
  parent account that must resolve it, its kind, what is being requested, the amount and currency
  when the request is financial, its status, when it was raised, when it expires, the note attached
  to its resolution if any, who resolved it, and when.
- **FR-142**: System MUST support exactly these request kinds: joining a trainer, a payment in USD,
  and a spend of tokens. The join-a-trainer kind MUST be carried out by this feature. The payment and
  token kinds MUST have their rules and their recorded data in place here, while the act of taking
  payment and of debiting tokens belongs to Epic-05; a request of either kind MUST NOT be marked
  approved until that act can be performed.
- **FR-143**: System MUST support exactly these request statuses — Pending Parent Approval, Info
  Requested, Approved, Denied, Expired, and Withdrawn — and MUST permit only these transitions: from
  Pending Parent Approval to any of Info Requested, Approved, Denied, Expired, or Withdrawn; and from
  Info Requested back to Pending Parent Approval or on to Denied, Expired, or Withdrawn. Approved,
  Denied, Expired, and Withdrawn MUST be terminal.
- **FR-144**: System MUST NOT carry out the action a request concerns while that request is in any
  status other than Approved, and MUST carry it out exactly once when the request becomes Approved.
- **FR-145**: System MUST always require parent approval for a payment in USD, and MUST provide no
  setting, per child or otherwise, capable of waiving it.
- **FR-146**: System MUST hold, per child profile, a parent-owned setting governing whether that child
  may spend tokens without approval, defaulting to off. While it is off a token spend MUST follow the
  same approval workflow a USD payment follows. While it is on a token spend MUST proceed immediately
  and the parent MUST receive a notice that reports what happened without asking them to decide
  anything.
- **FR-147**: System MUST keep the token setting independent for each child, MUST allow the parent to
  change it at any time, and MUST leave every already-pending request unaffected by a change, neither
  approving nor denying it.
- **FR-148**: System MUST notify the parent by email and in the application the moment a request is
  raised, naming the child, what is requested, and the amount and currency when the request is
  financial.
- **FR-149**: Parents MUST be able to see a list of the requests awaiting them showing, for each, the
  child, what is asked, the amount if any, when it was raised, and how long remains before it
  expires.
- **FR-150**: Parents MUST be able to approve, deny, or ask for more information on any request
  awaiting them, and MUST be able to attach a note to any of those three responses.
- **FR-151**: System MUST carry out an approved request's action under exactly the permissions and
  validation that would apply had the parent performed it directly. When the action cannot be
  completed — the invitation link has been revoked, the trainer is no longer Active, the profile has
  been removed — the platform MUST tell the parent why, MUST NOT record the request as Approved, and
  MUST leave it awaiting a further decision.
- **FR-152**: System MUST refuse to carry out an approved financial request whose amount no longer
  matches the amount the parent was shown, failing the request rather than proceeding at a different
  figure.
- **FR-153**: System MUST show the child, in their own view, the status of every request they raised
  and the moment it changes, and MUST deliver the parent's note to the child when the parent denied
  the request or asked for more information.
- **FR-154**: Children MUST be able to withdraw a request they raised while it is still awaiting a
  decision, which closes it as Withdrawn without carrying out the action and removes it from the
  parent's list.
- **FR-155**: System MUST expire a request 48 hours after it was raised when no decision has been
  taken. Expiry MUST have the effect of a denial, MUST NOT carry out the action, and MUST notify both
  the parent and the child. A return from Info Requested to Pending Parent Approval MUST NOT restart
  that 48-hour clock.
- **FR-156**: System MUST restrict the resolution of a request to the parent account that owns the
  child profile, and to a Super Admin acting in support. A child MUST NOT resolve their own request,
  and no one MUST be able to resolve a request twice — where two attempts arrive together, exactly
  one MUST take effect and the other MUST be told the request has already closed.
- **FR-157**: System MUST NOT allow a request belonging to a parent account that has left Active
  status to be resolved by anyone, MUST NOT approve it automatically, and MUST let it expire on its
  original schedule.
- **FR-158**: System MUST record every approval decision in the audit trail under FR-054 and FR-055,
  naming the child profile, the request, the decision taken, the account that took it, any note, and
  the time.
- **FR-159**: System MUST present a parent's awaiting requests through the navigation frame FR-062
  describes, carrying a count while any are pending, so the workflow satisfies the reachability rule
  FR-105 sets.

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
- **Player Profile** *(was Player Detail; widened by the 2026-08-27 extension)*: One player who
  trains. Holds first and last name, age, gender, optional school, photo and jersey number, the
  trainer-assigned skill level the family cannot edit, and which kind of player it is. One or more per
  Player/Parent account — at most one of the account holder's own kind, any number of children's.
  The subject of every trainer association, every context, and every approval request. Removed
  softly, never erased, so history stays attached.
- **Player Profile Kind**: The fixed pair of values distinguishing the account holder's own player
  profile from a child's. Governs the permitted age range, whether a sign-in may be granted, and how
  the profile is grouped in a context switcher.
- **Parent Contact Detail**: Emergency contact information and the family phone number, held against
  the Player/Parent account rather than against any individual child profile. One per account,
  serving every child on it.
- **Child Sign-In Account**: A child's own means of entry, when the parent grants one — a
  Player/Parent account holding the email address the parent supplied, tied to exactly one child
  profile and to the parent's account. Carries no contact details of its own and receives no mail but
  its own password setup and reset. Revocable by the parent, suspended while the parent is not
  Active, and ended when the child profile is removed.
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
- **Trainer–Player Association** *(subject narrowed by the 2026-08-27 extension)*: The fact that one
  **player profile** trains with one Trainer. Holds the trainer, the player profile, the invitation
  link that produced it, when it was formed, and its status. Many per profile and many per trainer;
  the pair is unique. Independent of every other profile's associations on the same account. Survives
  the erasure and the deactivation of either side, and survives its own removal as inactive history.
- **Active Training Context** *(was Active Trainer Context; widened by the 2026-08-27 extension)*:
  Which player profile and which of that profile's trainers a signed-in family member is currently
  looking at. Exactly one pair per signed-in account at a time, remembered against the account so it
  is the same wherever they sign in, and the boundary that scopes every view they see — separating
  siblings from each other as strictly as it separates trainers.
- **Approval Request**: One thing a child has asked for that a parent must decide. Holds the child
  profile, the parent account responsible, the kind, what is being requested, the amount and currency
  when financial, the status, when it was raised, when it expires, the resolving account, the note
  attached to the resolution, and when it was resolved. Many per child; at most one pending per child
  and subject at a time.
- **Approval Request Kind**: The fixed set of things a child may ask for — joining a trainer, a
  payment in USD, a spend of tokens. Determines whether approval can ever be waived and which epic
  carries the action out.
- **Approval Request Status**: The fixed set of states a request passes through — Pending Parent
  Approval, Info Requested, Approved, Denied, Expired, Withdrawn — with the last four terminal. Only
  Approved permits the requested action to happen, and it permits it exactly once.
- **Child Token Spending Setting**: A parent-owned permission, held per child profile, deciding
  whether that child's token spends wait for approval. Defaults to requiring approval, is changeable
  at any time, never affects a request already pending, and can never waive a USD payment.
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
- **SC-027**: A parent can add a child and place them with a trainer, from opening the family page to
  the child appearing on that trainer's roster, in under 2 minutes.
- **SC-028**: Across a test set of accounts holding a parent and three children on overlapping
  trainers, 100% of views show exactly one player profile and one trainer, and no view returns a
  sibling's or the parent's data.
- **SC-029**: 100% of the actions FR-132 forbids a child are refused when submitted directly to the
  platform rather than through its interface, verified by a permission test covering every forbidden
  action.
- **SC-030**: A child who follows a new trainer's invitation link is associated with nobody in 100% of
  attempts, and the parent's email arrives within 1 minute, exactly once per child-and-trainer pair
  however many times the child repeats the attempt.
- **SC-031**: 100% of child-initiated requests that need approval are recorded as Pending Parent
  Approval and have no effect until approved, verified by inspecting the subject of the request after
  the request is raised and before any decision.
- **SC-032**: A parent is notified of a new request, by email and in the application, within 1 minute
  of it being raised, and can go from that notice to a decision in under 1 minute.
- **SC-033**: An approved join request results in the child being on the trainer's roster within 5
  seconds of the decision, and the child sees the status change without signing out.
- **SC-034**: 100% of requests left untouched for 48 hours are recorded as expired, have not carried
  out their action, and have notified both the parent and the child — verified against a fixed clock.
- **SC-035**: 100% of USD payment requests require approval regardless of every setting combination
  tested, including every state of the per-child token setting.
- **SC-036**: With unsupervised token spending off, 100% of a child's token spends wait for approval;
  with it on, 100% complete immediately and produce an informational notice to the parent that
  requests no decision.
- **SC-037**: Changing one child's token setting leaves the other children's settings and 100% of
  already-pending requests unchanged.
- **SC-038**: In 100% of attempts to resolve one request twice — including two parent sessions
  approving simultaneously, and an approval racing the 48-hour expiry — exactly one decision takes
  effect and the underlying action happens either fully or not at all.
- **SC-039**: 100% of approval decisions, including expiries, produce an audit entry naming the child
  profile, the request, the decision, the actor, and the time.
- **SC-040**: No trainer-facing view or export reveals a player profile on the same account that does
  not train with that trainer, verified across every view available to a Trainer and to a Coach.
- **SC-041**: Deactivating a parent stops 100% of that account's child sign-ins and leaves 100% of
  its pending requests unresolvable within 1 minute, with none approving automatically.

## Out of Scope

The following Epic-01 items are deliberately excluded from this feature and belong to later slices:

- Coach invitation links: the single-use, one-person, seven-day variety and the rule that a coach
  works for exactly one trainer (US-01.08). The invitation link record carries a kind so this can
  be added without restructuring, but no such link is issued here.
- Reporting and analytics over invitation link usage, including conversion and referral tracking
  (Epic-06). Usage is recorded here; only later epics read it as analytics.
- Trainer-side management of an existing association — a Trainer removing a player from their own
  roster. The *parent* side of US-01.04 is in scope as of the 2026-08-27 extension; the trainer's
  ability to end an association from their end is not.
- Branding beyond one logo and one primary colour: separate light and dark logos, font choices,
  and layout customization are Phase 2 in the epic.
- The *execution* of the two financial approval kinds, though not their rules or their recorded
  data. Taking a payment in USD and debiting a token balance belong to Epic-05, and the events a
  child would be paying to attend belong to Epic-02. The approval workflow ships complete and
  demonstrable in this feature through the join-a-trainer kind (FR-142); a payment or token request
  cannot be approved until Epic-05 can carry it out.
- Parent approval of a child's RSVP and of a child cancelling an RSVP, which US-01.06 also lists.
  Reservations do not exist until Epic-02, so no second request kind with no subject is specified
  here; the mechanism FR-141 to FR-159 define absorbs them as further kinds without restructuring.
- Moving a child onto an independent account of their own — whether on turning 18 or at any other
  point. Epic-01's business rules place everyone under 18 on a parent-managed account and its open
  question Q-01.05 about 16-to-18-year-olds is resolved in favour of that rule, so no transition out
  of the family is specified.
- A second adult sharing management of the same child, and any transfer of a child profile between
  accounts. One account owns each child profile.
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

**Assumptions added with the 2026-08-27 extension**

- **How a child signs in** *(decided with the requester)*: Epic-01 says a child "can optionally have
  separate login (shares parent's contact info)" without saying what they sign in *with*, while
  FR-001, FR-004 and FR-008 identify and authenticate every account by a unique email address. The
  decision taken is that the parent supplies a distinct email address for the child, which becomes
  that child's login under the existing uniqueness rule, and that "shares parent's contact info" is
  honoured by routing every notification to the parent and holding no contact detail on the child
  (FR-129, FR-130). This leaves the ratified authentication model untouched. The known cost is that a
  child with no email address of their own cannot be given a sign-in; that family uses the parent's
  context switcher instead, which is no loss of capability.
- **The approval workflow is one mechanism, not three** *(decided with the requester)*: Epic-01
  describes the same wait-for-the-parent behaviour three times over — for a USD payment, for a token
  spend, and, in US-01.06, for a child asking to join a trainer. It is assumed to be a single
  mechanism with a kind, rather than three separate workflows, so the rules stated once apply
  identically to all three and later kinds (RSVPs, cancellations) need no restructuring.
- **Why the join-a-trainer kind carries the workflow now**: Events, payments and tokens arrive with
  Epic-02 and Epic-05, so a purchase-only workflow would be a schema with nothing to approve and no
  way to demonstrate. US-01.06's blocked invitation link is a genuine child-initiated request whose
  subject exists in this feature today, so it is assumed to be the first implemented kind and the
  vehicle by which the whole workflow is tested (FR-138, FR-142).
- **Approval statuses**: Epic-01 names "Pending Parent Approval", approve, deny, "request more info",
  and expiry. Two states are assumed beyond that list: *Info Requested* as a distinct status, because
  "request more info" must be visible as something other than plain pending; and *Withdrawn*, because
  a child who changes their mind should be able to clear their own request rather than leaving the
  parent to deny it. Neither weakens the epic's rules.
- **The 48-hour clock runs from the request**: Epic-01 states requests expire after 48 hours but not
  what happens when a parent asks for more information partway. It is assumed the clock runs from
  when the request was raised and is *not* restarted by that exchange, so a request cannot be held
  open indefinitely by repeated questions.
- **Expiry is a denial**: Epic-01 says expiry is an "auto-deny with notification". It is assumed to be
  recorded as its own status rather than as an ordinary denial, so a parent who never saw the request
  is distinguishable in the record from one who considered it and said no.
- **Approval carries the action out**: Epic-01 says "Approve (payment processed)". It is assumed the
  platform performs the action on the parent's behalf, under the parent's permissions, rather than
  merely unlocking it for the child to complete — and consequently that an approval whose action
  fails must not be left recorded as approved (FR-151).
- **A price that has moved invalidates the request**: Epic-01 does not address an amount changing
  between request and decision. It is assumed the parent must never be charged a figure they were not
  shown, so the request fails rather than proceeding (FR-152). The alternative — charging the new
  amount — was rejected as a consent problem.
- **Associations belong to profiles, not accounts**: Epic-01 requires each child to have their own
  trainers, calendar and availability, which cannot be expressed while an association joins an
  account to a trainer. Moving the association's subject to the player profile is assumed to be the
  intended structure, and FR-114 states it explicitly because it revises requirements the earlier
  slices already implemented.
- **Siblings are isolated from each other**: Epic-01 states a child cannot view the parent's training
  but is silent on siblings. Isolation between siblings is assumed to be as strict as isolation
  between trainers, since a child having a window into a sibling's schedule and spending would be a
  surprising reading of "limited permissions".
- **The trainer sees the child and the responsible adult**: Epic-01 requires the parent to own the
  family's contact information and requires trainers to see their own roster. It is assumed a trainer
  associated with a child sees that child plus the parent's contact details — they must be able to
  reach the adult — and sees no sibling who does not train with them (FR-116).
- **A child's own age boundary**: Child profiles run 1 to 18 and the account holder's own profile is
  18 or over, carried over unchanged from FR-077 rather than restated as a new rule. Nothing is
  specified about a child crossing 18, and FR-108 deliberately does not invalidate a profile that
  does.
- **Duplicate children are warned about, not prevented**: Epic-01 asks for a duplicate check on
  similar name and age. Because twins and a child named after a parent are both ordinary, it is
  assumed to be a warning the parent may overrule rather than a refusal (FR-110).
- **Removing a child is a soft removal**: Epic-01 says a removed child-trainer relationship is
  "soft-deleted (history preserved)". The same treatment is assumed for removing a child profile
  altogether, consistent with how FR-038 treats a deactivated account, so a trainer's past rosters
  and totals never change retrospectively.
- **A child cannot act while the parent cannot**: Epic-01 does not say what happens to a child's
  sign-in when the parent is deactivated. It is assumed to stop with the parent's (FR-136), because a
  child able to commit the family while the responsible adult is locked out would defeat the purpose
  of the approval workflow.
- **Notification volume**: Epic-01 specifies which notifications are sent but not how often. It is
  assumed that a repeated identical request produces no repeated email (FR-139) and that a parent
  receives one notice per event rather than one per child, since the approval list is the system of
  record and email is only the prompt to look at it.
- **Cancelling reservations on removal**: The removal prompt states that upcoming reservations will be
  cancelled, as Epic-01 words it. Reservations do not exist until Epic-02, so this feature is assumed
  to state the consequence and to leave the cancellation itself to the epic that creates the thing
  being cancelled.
