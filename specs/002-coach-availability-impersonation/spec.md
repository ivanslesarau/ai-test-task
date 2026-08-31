# Feature Specification: Coach Invitations, Availability ("My Times") & Super Admin Impersonation

**Feature Branch**: `002-coach-availability-impersonation`

**Created**: 2026-08-28

**Status**: Draft

**Input**: User description: "Complete the implementation of Epic-01 from the Task/Epics/Epic-01_User_Management_Authentication_SPEC.md file. Prepare specifications for coach invitations (US-01.08), the availability management system ("My Times" – US-01.09, US-01.10), and the user impersonation system (US-01.07)."

**Source Epic**: Epic-01 — User Management & Authentication. This specification covers the three
Epic-01 stories that feature `001-user-roles-admin` deliberately left out and listed in its own Out
of Scope section: **US-01.08** (a Trainer invites a Coach), **US-01.09** and **US-01.10** (the
availability system the epic calls "Best Times" for players and "My Times" for coaches), and
**US-01.07** (Super Admin impersonation). Completing these three closes Epic-01.

**Relationship to feature 001**: Everything feature 001 specified stands unchanged. This feature adds
to it and changes nothing it established. It relies on five things 001 already delivers: the four
closed roles and the three account states; sign-in, sessions, and the rule that permissions are
enforced when a request is received rather than by hiding a control; the invitation-link mechanism
players join through, whose records already carry a *kind* so a second kind is additive; the player
profile — one per person on a Player/Parent account, the account holder's own plus one per child —
and the profile switcher a parent already uses; and the append-only audit trail. Requirement numbers
here start again at FR-001 and are local to this feature; where a requirement of feature 001 is
relied upon it is named explicitly as "001 FR-0xx".

**Scope in one sentence**: A trainer can bring a coach onto their roster; every coach and every
player profile can state the times of the week they are available, and the trainers they train with
can read those times; and a Super Admin can view the platform as another person, under a visible
banner, on a one-hour leash, with an unforgeable record of having done so.

**Deliberate boundary**: Availability is delivered here as *stated times plus the per-person view of
them*. The two consumers the epic describes for that data — the roster-wide filter ("show players
available Monday 5–8pm", "15 of 20 players available at this time") and the coach-to-event conflict
warning with a trainer override — both require an event or a roster-wide query that does not exist in
the platform yet, and are deferred with their reasons in Out of Scope. This feature makes the data
exist, correct and visible; the epics that schedule against it consume it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A Trainer Invites a Coach and Tracks the Invitation (Priority: P1)

A trainer opens the Coaches section of their portal and invites a coach by email address, optionally
addressing them by name and adding a personal message ("Hi Sam — this is the link for the spring
program"). The platform sends that person an invitation that admits exactly one person, once, within
seven days. The trainer's Coaches section then shows the invitation and what has become of it —
awaiting a response, accepted, expired, revoked, or blocked because the person could not be admitted
— so the trainer knows whether to follow up, re-send, or give up, without having to ask anyone.

**Why this priority**: A trainer with no coaches cannot delegate a single session, and no coach can
reach the platform by any other route — there is no self-registration for coaches and no Super Admin
route that attaches a coach to a trainer. This is the only door, so it is the first thing that must
work. It is also self-contained: it delivers value to the trainer before any coach accepts, because
issuing and tracking invitations is itself the trainer-side workflow.

**Independent Test**: Sign in as a Trainer, invite two email addresses, and confirm both appear with
their state, expiry date, and the message sent; re-send one and confirm the earlier link stops working
while the new one works; revoke the other and confirm the link is refused with a plain explanation. No
coach needs to accept anything for this story to be demonstrated.

**Acceptance Scenarios**:

1. **Given** a Trainer with an Active account, **When** they invite a coach by email address with an
   optional name and message, **Then** the platform issues an invitation that stops working seven days
   later, sends it to that address carrying the trainer's name and the message, and shows it in the
   trainer's Coaches section as awaiting a response.
2. **Given** an invitation that is awaiting a response, **When** the trainer re-sends it, **Then** a
   fresh seven-day invitation is delivered, the previous link no longer admits anyone, and the trainer
   sees one invitation with a new expiry date rather than two.
3. **Given** an invitation that is awaiting a response, **When** the trainer revokes it, **Then**
   anyone following that link is told plainly that the invitation is no longer valid, and the trainer
   sees it as revoked.
4. **Given** an invitation issued more than seven days ago that nobody used, **When** the trainer
   looks at their Coaches section, **Then** it reads as expired and offers to re-send.
5. **Given** an address that already holds an invitation awaiting a response from the same trainer,
   **When** the trainer tries to invite that address again, **Then** the platform declines to create a
   second invitation and points at the existing one, offering to re-send or revoke it.
6. **Given** a Trainer, **When** they seek any invitation belonging to another trainer by any route,
   **Then** nothing about it is returned to them.

---

### User Story 2 - A Coach Accepts an Invitation and Joins Exactly One Trainer (Priority: P1)

The invited person opens the link in their mail. If they have no account they set one up — name,
password, phone, and the professional details a coach presents — and the platform makes them a Coach
on that trainer's roster, without ever asking them to pick a role or find the trainer, because the
invitation already says both. If they already hold a coach account they sign in and accept with it.
Either way they land in a coach portal carrying that trainer's brand, and the trainer sees them in the
Coaches list. A coach works for one trainer and one only: someone already on a roster cannot join a
second, and is told so without being told whose roster they are on.

**Why this priority**: Story 1 issues invitations; without this story none of them lead anywhere and
the Coach role remains a role no living account can hold. Together the two stories are the minimum
viable slice of US-01.08.

**Independent Test**: With an invitation in hand, follow the link as a brand-new person, complete
setup, and confirm the coach appears on that trainer's roster and sees that trainer's portal; then
take a second trainer's invitation to the same coach and confirm it is refused and names no trainer.

**Acceptance Scenarios**:

1. **Given** a valid invitation and a person with no account, **When** they follow the link and
   complete account setup, **Then** they hold a Coach account, they are on the inviting trainer's
   roster from that moment, the invitation is spent, and they were never asked to choose a role or a
   trainer.
2. **Given** a valid invitation and a person who already holds a Coach account at the invited address
   and is on no roster, **When** they follow the link and sign in, **Then** they join the inviting
   trainer's roster and keep their existing profile, stated times, and history.
3. **Given** a coach already on another trainer's roster, **When** they follow an invitation from a
   second trainer, **Then** acceptance is refused with an explanation that they already work with a
   trainer, the message names no trainer and no other person, the invitation is not spent, and the
   inviting trainer sees the invitation as blocked rather than as accepted.
4. **Given** a coach already on the inviting trainer's roster, **When** they follow another invitation
   from that same trainer, **Then** they are told they are already on this roster and nothing changes
   — no duplicate assignment is created.
5. **Given** an account whose role is not Coach — a trainer, a player or parent, a Super Admin —
   **When** it follows a coach invitation, **Then** acceptance is refused with an explanation, and no
   account's role is changed by following a link.
6. **Given** a spent, revoked, or expired invitation, **When** anyone follows it, **Then** they are
   told plainly why it cannot be used, and are given nothing that would help them guess at another.
7. **Given** an invitation whose inviting trainer has since left Active status, **When** the invited
   person follows it, **Then** acceptance is refused and they are told the invitation is not valid.
8. **Given** a coach on a roster, **When** the trainer ends that assignment, **Then** the coach is on
   no roster, sees none of that trainer's data, keeps their own account, profile, and stated times,
   and is free to accept another trainer's invitation.

---

### User Story 3 - A Coach Sets Their My Times (Priority: P2)

A coach opens "My Times" and states, for each day of the week, the ranges they can work — "Monday
4:00 PM–6:00 PM and 7:00 PM–9:00 PM, Saturday 9:00 AM–12:00 PM" — leaving the other days empty to say
they cannot work them. They save the week in one action and are told it was saved and who will see it.
It is a standing weekly pattern, not a diary: they set it once and revise it when their life changes.

**Why this priority**: This is the coach half of the availability system and the input a trainer's
planning depends on. It ranks below the invitation stories because a coach must exist before a coach
can state times, and above the trainer-side view because the view has nothing to show until somebody
states something.

**Independent Test**: Sign in as a coach, state times on three days including two ranges on one day,
save, sign out and back in, and confirm the week reads back exactly as entered; then submit
overlapping ranges and confirm the save is refused with the day named and the stored week unchanged.

**Acceptance Scenarios**:

1. **Given** a coach who has never set their times, **When** they open My Times, **Then** they see an
   empty week presented as "no times set" — not as unavailable — with an explanation of what stating
   times will do.
2. **Given** a coach on the My Times view, **When** they add one or more ranges to any day and save,
   **Then** the whole week is saved as one unit, they are told it was saved and that the trainer they
   work with can see it, and the week reads back exactly as entered on any later visit.
3. **Given** a coach with times on a day, **When** they add a second range on that same day that does
   not overlap the first, **Then** both are kept.
4. **Given** a coach, **When** they submit two ranges that overlap on the same day, or a range whose
   start is not before its end, **Then** the save is refused, nothing in the stored week changes, and
   the message names the day and the problem.
5. **Given** a coach with a stated week, **When** they clear it, **Then** their times read as "no
   times set" again and no trainer sees a stale week.
6. **Given** a coach, **When** they seek anyone else's stated times by any route, **Then** nothing is
   returned — a coach sees their own times and no one else's.

---

### User Story 4 - A Parent Sets Availability Separately for Themselves and Each Child (Priority: P2)

A parent opens Availability and states the times their family can attend. Because one account can hold
their own player profile and a profile per child, they state a separate week per profile, choosing
whose week they are editing with the profile switcher they already use everywhere else. Grace trains
Tuesdays and Thursdays after school; Leo can only make Saturday mornings; the parent records both, and
each child's week is their own. A player on their own account does the same for their single profile,
and a child with their own sign-in can state and revise their own times but nobody else's.

**Why this priority**: This is the player half of the availability system — the larger population, and
the one whose times the epic wants sessions planned around. It is separated from Story 3 because it
carries a rule the coach side does not have: one account, several people, strictly separated weeks.

**Independent Test**: Sign in as a parent with two child profiles, state a different week for each
child and for the parent's own profile, and confirm each reads back against the right profile and that
no profile shows another's times; then sign in as one of the children and confirm they see and can
change only their own week.

**Acceptance Scenarios**:

1. **Given** a parent with their own player profile and two child profiles, **When** they state times
   for one child, **Then** those times belong to that child's profile alone, and the other child's and
   the parent's own week are untouched.
2. **Given** a parent editing availability, **When** they switch profiles, **Then** the week shown
   changes to the profile now selected, and it is unmistakable whose times are on screen.
3. **Given** a player or parent, **When** they save a week, **Then** they are told it was saved and
   that the trainers they train with can see it when planning sessions.
4. **Given** a signed-in child, **When** they open Availability, **Then** they can view and change the
   times for their own profile and reach no profile belonging to a parent or a sibling.
5. **Given** a child who has stated their own times, **When** the parent opens that child's
   availability, **Then** the parent can see and revise it — the parent's authority over a child
   profile extends to its times.
6. **Given** any player or parent, **When** they seek a profile that is not on their account by any
   route, **Then** nothing about it, including its times, is returned.
7. **Given** a child profile with stated times, **When** that profile is removed from the account,
   **Then** its times go with it and appear in no view.

---

### User Story 5 - A Trainer Reads the Stated Times of Their Coaches and Players (Priority: P2)

A trainer planning next month opens a coach or a player and sees, without hunting for it, a short
summary of when that person is available — "Best times: Mon 5–8pm, Wed 6–9pm" — with the full week
behind it and the date the person last revised it, so a summary from eight months ago is visibly old.
People who have stated nothing read as "no times set", which is information too: it means ask them,
not that they are unavailable. The trainer sees this for the coaches on their roster and the players
who train with them, and for nobody else.

**Why this priority**: Stated times are worth nothing to the business until the person planning
sessions can read them; this is what turns Stories 3 and 4 from data entry into a scheduling aid. It
sits at P2 with them rather than P1 because a trainer can still plan without it, as they do today.

**Independent Test**: With a coach and two players who have stated times and one who has not, sign in
as their trainer and confirm each record shows the right summary, the full week, and a last-revised
date, that the person with nothing set reads as "no times set", and that a player belonging only to a
different trainer appears nowhere.

**Acceptance Scenarios**:

1. **Given** a trainer with a coach on their roster who has stated times, **When** the trainer opens
   that coach, **Then** they see a plain-language summary of the week, the full detail, and when it
   was last revised.
2. **Given** a trainer and a player profile that trains with them, **When** the trainer opens that
   player, **Then** they see the same three things for that profile.
3. **Given** a person who has stated no times, **When** a trainer opens them, **Then** the record
   reads "no times set" and is not presented as unavailable.
4. **Given** a trainer, **When** they seek the times of a coach on another trainer's roster, or of a
   player profile that does not train with them, **Then** nothing is returned by any route.
5. **Given** a trainer viewing anyone's times, **When** they attempt to change them, **Then** they
   cannot — stated times are the person's own, and the trainer's access is read-only.
6. **Given** stated times for any person, **When** anyone acts anywhere in the platform, **Then**
   nothing is blocked, refused, or prevented on the grounds of stated times — they inform decisions,
   they do not gate them.

---

### User Story 6 - A Super Admin Views the Platform as Another Person (Priority: P3)

A trainer writes in: "the join link isn't working for my players". Rather than asking for screenshots
or guessing from logs, the Super Admin finds that trainer in the user directory, chooses Impersonate,
confirms the person and role in a prompt, and is looking at exactly what the trainer sees — the same
navigation, the same data, the same permissions, no more and no less. A conspicuously coloured banner
across the top says whose portal this is and offers the way out. The Super Admin reproduces the
problem, exits, and is back in their own view without signing in again. If they forget to exit, the
platform exits for them an hour after they started. Another Super Admin is the one thing they cannot
impersonate.

**Why this priority**: It is a support tool, not a path any customer walks: the platform is fully
usable without it, and the coach and availability slices above are visible product. It is nonetheless
the story with the largest security surface in this feature, which is why its rules are stated as
tightly as they are.

**Independent Test**: Sign in as a Super Admin, impersonate a trainer, and confirm the view, the data,
and the permissions are that trainer's, that the banner is present on every view reached, that Super
Admin-only views are unreachable while impersonating, that Exit returns to the admin's own view
without re-authentication, and that impersonating another Super Admin is refused.

**Acceptance Scenarios**:

1. **Given** a Super Admin on the user directory, **When** they choose Impersonate on a row and
   confirm a prompt naming the person and their role, **Then** they are placed in that person's view of
   the platform.
2. **Given** an impersonation in progress, **When** the Super Admin moves anywhere in the platform,
   **Then** a visually distinct banner naming the impersonated person and offering Exit is present on
   every view, and everything they can see and do is exactly what that person can see and do — no
   Super Admin capability is reachable and nothing of that person's is withheld.
3. **Given** an impersonation in progress, **When** the Super Admin chooses Exit, **Then** they are
   returned to their own Super Admin view with their own permissions, without signing in again.
4. **Given** an impersonation that began an hour ago, **When** the Super Admin does anything at all,
   **Then** the impersonation has already ended, they are in their own view, and they are told it ended
   because an hour had passed.
5. **Given** a Super Admin, **When** they attempt to impersonate another Super Admin account, their own
   account, or an account whose personal information has been erased, **Then** it is refused with an
   explanation and no impersonation begins.
6. **Given** an impersonation in progress, **When** the Super Admin attempts to change the person's
   password or email address, to deactivate or erase that account, or to start a second impersonation
   from within the first, **Then** each is refused — impersonation is for seeing and helping, not for
   taking an account over.
7. **Given** an impersonation in progress, **When** the impersonated person is using the platform at
   the same time, **Then** nothing about their session changes: they are not signed out, not
   interrupted, and their own sign-in state is untouched.
8. **Given** anyone who is not a Super Admin, **When** they attempt to start an impersonation by any
   route, **Then** it is refused when the request is received, not merely hidden from them.
9. **Given** an impersonation in progress, **When** the impersonated account leaves Active status or
   the Super Admin's own account does, **Then** the impersonation ends at once and the admin is
   returned to their own view or signed out accordingly.

---

### User Story 7 - A Super Admin Reviews the Impersonation History (Priority: P3)

Because impersonation lets one person act as another, the fact that it happened must be unforgeable. A
Super Admin opens Impersonation History and sees every impersonation the platform has ever permitted:
which admin, which person, when it started, when and how it ended — left, timed out, or ended by
sign-out — and how long it lasted. The history can be narrowed to one admin, one impersonated person,
or a date range, so a compliance question about a single account is answerable in one search. No one
can edit or delete a line of it.

**Why this priority**: Story 6 is not defensible without it — an impersonation feature with a
tamperable record is an audit finding — but it is a read-only report over data Story 6 writes, so it
follows it.

**Independent Test**: Perform three impersonations that end in the three different ways, then open
Impersonation History and confirm each appears once with the correct participants, times, duration,
and end reason, that filtering by admin and by impersonated person returns the right subsets, and that
no route offered anywhere alters or removes an entry.

**Acceptance Scenarios**:

1. **Given** completed impersonations, **When** a Super Admin opens Impersonation History, **Then**
   each appears once showing the admin, the impersonated person, start, end, duration, and how it
   ended.
2. **Given** an impersonation still in progress, **When** the history is opened, **Then** it appears as
   in progress with its start time and no end time.
3. **Given** a history with many entries, **When** a Super Admin narrows it to one admin, one
   impersonated person, or a date range, **Then** exactly the matching entries are returned.
4. **Given** a change made to any record while impersonating, **When** that change is examined in the
   platform's record of administrative actions, **Then** it names both the impersonated person and the
   Super Admin who acted, so no change made under impersonation is attributable to the person alone.
5. **Given** any account that is not a Super Admin, **When** it attempts to read the impersonation
   history, **Then** nothing is returned.
6. **Given** an entry in the history, **When** anyone attempts to alter or remove it by any route,
   **Then** it is refused and the entry stands.

---

### Edge Cases

**Coach invitations**

- The invited address belongs to a Coach account whose status is Inactive: the person cannot sign in
  at all, so acceptance cannot proceed; they are told their account is not active and to contact
  support, and the invitation is left unspent so it still works once the account is restored.
- The invited address belongs to an erased account: the invitation cannot be accepted, and the refusal
  reveals nothing about why the address is unusable.
- The invited person forwards the link to a colleague, who signs in with a different address: the
  invitation is refused, because it was addressed to one person; the message says which address it was
  issued for, which the holder of the mail already knows.
- Two people open the same invitation at the same moment and both accept: exactly one acceptance takes
  effect; the other is told the invitation has already been used.
- The trainer revokes an invitation in the same moment someone accepts it: one of the two wins cleanly
  — either the coach is on the roster and the invitation shows as accepted, or the coach is refused and
  it shows as revoked. No state exists where both are true.
- The trainer's account leaves Active status while an invitation is outstanding: it stops being
  acceptable, and re-activation makes it acceptable again if it has not otherwise expired.
- A coach's assignment ends while they are signed in: their next action shows them a portal attached to
  no trainer, not a portal still showing the former trainer's data.
- The trainer invites their own address, or the address of one of their own players: the first is
  refused at acceptance because the address holds a Trainer account, the second because the role is not
  Coach — and in neither case does the platform tell the trainer at invite time whether the address
  already has an account.

**Availability**

- A range that would run past midnight: the day ends at midnight, so such a range is refused with an
  explanation; a person who works past midnight states the remainder on the following day.
- Two ranges that touch exactly — one ending at 6:00 PM, the next starting at 6:00 PM: allowed, and
  may be presented as a single block.
- A range shorter than the smallest unit the platform accepts, or one whose start equals its end:
  refused with the day named.
- Absurd volume — dozens of ranges on one day: refused above the stated ceiling per day, so no view has
  to render an unbounded list.
- Two devices save the same person's week at once: the later complete save wins; no week is ever half
  saved, and a refused save leaves the previous week exactly as it was.
- A player trains with three trainers: one stated week serves all three. There is no per-trainer week
  in this feature, and every trainer they train with sees the same times.
- A player leaves a trainer: that trainer stops seeing their times immediately, and the times stay with
  the player for the trainers that remain.
- An account is deactivated: its stated times are preserved untouched, and the platform does not
  present a deactivated person as available.
- A coach on no roster states times: permitted and kept, so their week is ready the day they join a
  trainer; nobody but them can see it in the meantime.

**Impersonation**

- The Super Admin closes the tab without exiting: the impersonation ends on the hour deadline, and the
  history records that it ended by timeout rather than leaving an entry open forever.
- The Super Admin signs out while impersonating: the impersonation ends first and is recorded as ended
  by sign-out; no session is left that could resume it.
- The impersonated person acts at the same moment the Super Admin does: neither acts with special
  privilege, so the outcome is whatever the platform's ordinary rules produce for two concurrent
  actors, and the admin's change is recorded as theirs.
- The impersonated person is a child with their own sign-in: impersonation is permitted, and every
  restriction that binds that child binds the admin while impersonating them.
- The impersonated person is a parent: the admin sees the whole family exactly as the parent does,
  including profiles they could not otherwise reach, and the record makes plain who looked.
- A second Super Admin impersonates the same person at the same time: both are permitted, and both are
  recorded separately.
- The same Super Admin starts a new impersonation while one is in progress: the first ends and is
  recorded before the second begins; only one is ever active per admin.
- The impersonated account is erased mid-session: the impersonation ends at once, and the history entry
  survives the erasure, naming the account by identifier rather than by the personal details erasure
  removed.

## Requirements *(mandatory)*

### Functional Requirements

**Coach invitations — issuing and tracking (US-01.08, trainer side)**

- **FR-001**: Trainers MUST be able to invite a coach by email address. The address is required; the
  invited person's name and a personal message are optional, and when not given are absent rather than
  blank.
- **FR-002**: System MUST make each coach invitation admit exactly one person exactly once, and MUST
  stop it being usable seven days after it was issued. This differs deliberately from the standing
  player link of 001 FR-065, which never expires and admits any number of people.
- **FR-003**: System MUST deliver each invitation to the invited address, carrying the inviting
  trainer's name and brand, the personal message when one was given, the link, and the date the
  invitation stops working.
- **FR-004**: Trainers MUST be able to see every coach invitation they have issued, each showing the
  invited address, the name and message sent, when it was issued, when it stops working, and its
  state: awaiting a response, accepted, expired, revoked, or blocked because the invited person could
  not be admitted.
- **FR-005**: Trainers MUST be able to re-send an invitation that is awaiting a response or has
  expired. Re-sending MUST issue a fresh seven-day admission, MUST make the previous link unusable,
  and MUST leave one invitation for that address rather than two.
- **FR-006**: Trainers MUST be able to revoke an invitation that is awaiting a response, after which
  following the link MUST be refused with a plain statement that it is no longer valid.
- **FR-007**: System MUST decline to issue a second invitation to an address that already holds one
  awaiting a response from the same trainer, and MUST point the trainer at the existing invitation with
  the option to re-send or revoke it.
- **FR-008**: System MUST NOT reveal at invite time whether the invited address already holds an
  account, so that the invitation view cannot be used to discover who is on the platform.
- **FR-009**: System MUST restrict every view of and action on a coach invitation to the trainer who
  issued it, and to a Super Admin acting in support. No other trainer, coach, player, or parent may
  read, re-send, or revoke it by any route, enforced when the request is received under 001 FR-015.
- **FR-010**: System MUST NOT allow a trainer whose account is not Active to issue or re-send an
  invitation, and MUST refuse acceptance of an outstanding invitation while the inviting trainer's
  account is not Active.

**Coach invitations — acceptance and the one-trainer rule (US-01.08, coach side)**

- **FR-011**: A person following a valid coach invitation who holds no account MUST be able to
  establish one — their name, a password, their phone number, and the professional details a coach
  presents — and MUST NOT be asked to choose a role or to identify the trainer, both of which the
  invitation already determines.
- **FR-012**: A person following a valid coach invitation who already holds a Coach account at the
  invited address MUST be able to accept with that account, keeping their existing profile, stated
  times, and history.
- **FR-013**: System MUST require that the account accepting an invitation carries the address the
  invitation was issued to, and MUST refuse any other account with a message naming the address the
  invitation was issued for.
- **FR-014**: System MUST refuse acceptance by an account whose role is not Coach, and MUST NOT change
  any account's role as a consequence of following a link.
- **FR-015**: System MUST allow a coach to be assigned to at most one trainer at any time. An attempt
  to accept an invitation while already assigned MUST be refused, MUST NOT spend the invitation, and
  MUST NOT disclose the identity of the trainer the coach already works with.
- **FR-016**: System MUST treat acceptance by a coach already on the inviting trainer's own roster as a
  no-op that says so, creating no duplicate assignment and changing nothing.
- **FR-017**: System MUST place a coach on the inviting trainer's roster the moment they accept, with
  no further confirmation step, and MUST record the date they joined.
- **FR-018**: System MUST mark an invitation as spent on acceptance, and where two acceptances arrive
  together exactly one MUST take effect while the other is told the invitation has already been used.
- **FR-019**: System MUST show an invitation refused under FR-014 or FR-015 to the inviting trainer as
  blocked, so the trainer knows to stop waiting, while disclosing nothing about the invited person's
  account or about any other trainer.
- **FR-020**: Trainers MUST be able to see their roster of coaches, each showing the coach's name, the
  address they were invited at, the date they joined, whether their account is Active, and the summary
  of their stated times FR-034 requires.
- **FR-021**: Trainers MUST be able to end a coach's assignment. Afterwards the coach MUST be on no
  roster, MUST reach none of that trainer's data, MUST keep their own account, profile, and stated
  times, and MUST be free to accept another trainer's invitation.
- **FR-022**: System MUST tell a coach who is on no roster plainly that they are not attached to a
  trainer, and MUST show them no trainer's data.
- **FR-023**: System MUST record in the audit trail of 001 FR-054 every invitation issued, re-sent,
  revoked, accepted, and refused, and every assignment ended — naming the actor, the invitation, the
  coach where known, and the time.

**Availability — stating times (US-01.09, US-01.10)**

- **FR-024**: Coaches MUST be able to state, for each of the seven days of the week, the time ranges
  they are available, reached from the navigation frame of 001 FR-062 under the label "My Times".
- **FR-025**: Players and parents MUST be able to state the same, per player profile, reached from the
  same navigation frame under the label "Availability".
- **FR-026**: System MUST allow more than one range on the same day, and MUST treat a day with no range
  as a statement that the person is not available that day.
- **FR-027**: System MUST refuse a week containing a range whose start is not before its end, a range
  that would run past the end of the day, or two ranges that overlap on the same day; the refusal MUST
  name the day and the problem, and MUST leave the previously stated week exactly as it was. Ranges
  that touch exactly, one ending where the next begins, MUST be accepted.
- **FR-028**: System MUST resolve stated times to quarter-hour boundaries, MUST require every range to
  be at least one quarter-hour long, and MUST accept at most six ranges on any one day.
- **FR-029**: System MUST save a stated week as a single unit that replaces the previous week entirely,
  MUST never leave a partially saved week however the save fails or however many devices save at once,
  and MUST confirm to the person that it was saved and who can see it.
- **FR-030**: People MUST be able to clear their stated week, after which their times read as "no times
  set" and no view presents a stale week.
- **FR-031**: System MUST keep exactly one stated week per coach and one per player profile, serving
  every trainer that person trains with; there is no per-trainer week in this feature.
- **FR-032**: System MUST record when a stated week was last revised, and MUST make that date visible
  wherever the times are read.

**Availability — who may state and read whose times**

- **FR-033**: System MUST allow a person to state times only for themselves or for a player profile on
  their own account: a coach for their own week only; a parent for their own profile and each of their
  children's; a signed-in child for their own profile only, and for no parent's or sibling's,
  consistent with 001 FR-131 and FR-132.
- **FR-034**: Trainers MUST be able to read, for each coach on their roster and each player profile
  that trains with them, a plain-language summary of that person's stated week, the full week behind
  it, and the date it was last revised.
- **FR-035**: System MUST present a person who has stated nothing as "no times set" and MUST NOT
  present them as unavailable.
- **FR-036**: System MUST NOT disclose a person's stated times to any trainer who is not the coach's
  trainer or one of the player profile's trainers, to any coach other than the person themselves, or to
  any player or parent outside the account that owns the profile — by any view, export, or route,
  enforced when the request is received.
- **FR-037**: System MUST make a trainer's access to stated times read-only: a trainer MUST NOT be able
  to state or alter times on anyone else's behalf.
- **FR-038**: System MUST treat stated times as guidance only. Nothing anywhere in the platform may be
  blocked, refused, or prevented on the grounds of stated times in this feature.
- **FR-039**: System MUST remove a player profile's stated times when the profile is removed, MUST keep
  a coach's stated times when their assignment ends, MUST stop disclosing a player's times to a trainer
  the moment that association ends, and MUST preserve the stated times of a deactivated account without
  presenting that person as available.

**Impersonation (US-01.07)**

- **FR-040**: Super Admins MUST be able to start impersonation of a chosen account from the user
  directory, after confirming a prompt that names the person and their role.
- **FR-041**: System MUST restrict starting an impersonation to Super Admin accounts that are Active,
  enforced when the request is received rather than by withholding the control.
- **FR-042**: System MUST refuse to impersonate another Super Admin account, the requesting admin's own
  account, and any account whose personal information has been erased. Accounts that are Active and
  accounts that are Inactive MAY be impersonated, and an Inactive one MUST be labelled as such.
- **FR-043**: While an impersonation is in progress, System MUST present exactly the views, navigation,
  data, and permissions the impersonated person has — no Super Admin capability reachable, and nothing
  of that person's withheld.
- **FR-044**: System MUST display, on every view reached during an impersonation, a persistent and
  visually distinct banner naming the impersonated person and offering an immediate way out.
- **FR-045**: Super Admins MUST be able to leave an impersonation at any moment and be returned to
  their own view with their own permissions, without signing in again.
- **FR-046**: System MUST end an impersonation automatically one hour after it began, and MUST also end
  it when the admin leaves it or signs out. When it ends on the deadline, the admin MUST be returned to
  their own view and told why.
- **FR-047**: System MUST refuse, while an impersonation is in progress, any change to the impersonated
  person's password or email address, any deactivation or erasure of that account, and any attempt to
  begin a second impersonation from within the first.
- **FR-048**: System MUST allow at most one impersonation at a time per Super Admin, ending and
  recording the one in progress before another begins.
- **FR-049**: System MUST leave the impersonated person's own sessions and sign-in state entirely
  untouched by an impersonation: they are not signed out, not interrupted, and not required to do
  anything.
- **FR-050**: System MUST end an impersonation immediately when the impersonated account leaves Active
  status or is erased, and when the Super Admin's own account leaves Active status.
- **FR-051**: System MUST record every impersonation: which Super Admin, which person, when it began,
  when it ended, how it ended — left, timed out, or ended by sign-out — and how long it lasted.
- **FR-052**: System MUST record every change made while impersonating in the audit trail of 001 FR-054
  naming both the impersonated person and the Super Admin who acted, so that no change made under
  impersonation is attributable to the impersonated person alone.
- **FR-053**: Super Admins MUST be able to read an impersonation history showing every impersonation,
  including any still in progress, with its participants, times, duration, and how it ended.
- **FR-054**: Super Admins MUST be able to narrow the impersonation history to one Super Admin, one
  impersonated person, or a date range.
- **FR-055**: System MUST make the impersonation history append-only — no account, Super Admin
  included, may alter or remove an entry by any route — and MUST keep entries intact after the
  impersonated account is erased, naming that account by identifier rather than by the personal details
  erasure removed.
- **FR-056**: System MUST restrict the impersonation history to Super Admin accounts, returning nothing
  to anyone else.

### Key Entities *(include if feature involves data)*

- **Coach Invitation**: One trainer's offer to one named address to become a coach on their roster.
  Carries the invited address, the optional invited name and personal message, who issued it and when,
  when it stops working, whether it has been used, revoked, or blocked, and — once accepted — which
  coach accepted it. Distinguished from the standing player invitation of feature 001 by being
  addressed to one person, admitting one person once, and expiring. Related to: Trainer, Coach.
- **Coach Assignment**: The fact that one coach works for one trainer, and since when. At most one per
  coach at any time; ending it leaves the coach unattached rather than erasing the record of having
  been attached. Related to: Coach, Trainer, Coach Invitation.
- **Stated Week (Availability)**: One person's standing weekly pattern of when they are available — a
  set of day-and-time ranges, at most six per day, on quarter-hour boundaries, none overlapping within
  a day — together with the date it was last revised. Exactly one per coach and one per player profile.
  Absence is meaningful and distinct from emptiness: "no times set" is not "unavailable". Related to:
  Coach, Player Profile, Trainer (read-only reader).
- **Impersonation Session**: One occasion on which a Super Admin viewed the platform as another person.
  Carries both participants, when it began, when and how it ended, and its duration; at most one open
  per Super Admin; capped at one hour. Related to: Super Admin, any impersonated account, Audit Entry.
- **Audit Entry** (existing, from feature 001): The append-only record of administrative actions.
  Extended in use, not in nature, by this feature: coach invitation and assignment events are recorded
  here, and every change made during an impersonation carries both the acting Super Admin and the
  impersonated person.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A trainer can invite a coach in under 60 seconds from opening their Coaches section, and
  the invited person can go from opening the mail to standing in a coach portal in under 4 minutes, so
  the epic's target of onboarding a coach in under 5 minutes is met end to end.
- **SC-002**: 100% of coach invitations are refused after they have been used once, after seven days,
  and after being revoked, verified by attempting each of the three.
- **SC-003**: 100% of attempts by a coach already assigned to a trainer to join a second trainer are
  refused, and no refusal message, view, or export reveals the identity of the trainer they already
  work with.
- **SC-004**: A trainer can determine the state of every invitation they have issued from one view,
  with no invitation in an unexplained state, verified across all five states.
- **SC-005**: 0 invitations lead to a role change, to a second simultaneous assignment for one coach,
  or to acceptance by an address the invitation was not issued to.
- **SC-006**: A person can state a full week of availability across three days in under 2 minutes, and
  a parent can do the same for a second child without leaving the availability view.
- **SC-007**: 100% of stated weeks read back exactly as entered after signing out and in again, and 0
  weeks are ever observed in a partially saved state, including when two devices save at once.
- **SC-008**: 100% of invalid weeks — overlapping ranges, a start at or after its end, a range past the
  end of the day, more than six ranges in a day — are refused with the day named, and in every such
  case the previously stated week is unchanged.
- **SC-009**: 0 instances of a trainer, coach, player, parent, or child reading stated times they are
  not entitled to, verified across every view and export available to each role, including sibling
  profiles on one family account.
- **SC-010**: A trainer opening a coach or a player reaches that person's stated times without leaving
  the record, and 100% of connected people show either a summary or "no times set".
- **SC-011**: 0 actions anywhere in the platform are blocked, refused, or delayed on the grounds of
  stated times.
- **SC-012**: A Super Admin is looking at another person's view within 10 seconds of deciding to, and
  the impersonation banner is present on 100% of views reached while impersonating.
- **SC-013**: 100% of attempts to impersonate a Super Admin account, one's own account, or an erased
  account are refused, and 100% of attempts to start an impersonation by an account that is not an
  Active Super Admin are refused when the request is received.
- **SC-014**: 0 impersonations exceed one hour, and 100% of impersonations appear exactly once in the
  history with both participants, a start, an end, a duration, and how they ended.
- **SC-015**: 100% of changes made during an impersonation are attributable to both the Super Admin and
  the impersonated person, and 0 entries of the impersonation history can be altered or removed by any
  account through any route.
- **SC-016**: While an impersonation is in progress, 0 Super Admin-only capabilities are reachable and 0
  of the impersonated person's own capabilities are withheld, verified across every view for each
  impersonable role.
- **SC-017**: A Super Admin can answer "was this account ever impersonated, by whom, and for how long"
  from the history in under 30 seconds for any named account.
- **SC-018**: A Super Admin can reproduce and diagnose a user-reported problem without a code
  deployment and without asking the user for their password, satisfying the epic's support metric.

## Out of Scope

The following are deliberately excluded from this feature. The first two are the parts of US-01.09 and
US-01.10 that cannot be built yet; the rest belong to later epics or to Epic-01's Post-MVP list.

- **The roster-wide availability query** — "show players available Monday 5–8pm", "15 of 20 players
  available at this time", and session-time suggestions derived from many people's stated times. This
  feature delivers the stated times and the per-person view of them; the filter belongs with the view
  that would carry it, which is event creation in Epic-02 or the player CRM in Epic-03. Building it
  here would produce a query with no screen to live on.
- **The coach-to-event conflict warning and the trainer's override** — the second half of US-01.10:
  warning a trainer who assigns a coach outside their stated times, requiring a reason, recording the
  override, and letting the coach accept or request a change. Every one of those clauses names an
  event, and no event exists in the platform until Epic-02. The stated times this feature delivers are
  exactly the input that mechanic will read, and Epic-01 open question Q-01.06 — whether a coach is
  notified when overridden — is deferred with it.
- **Date-specific availability**: holidays, one-off exceptions, "unavailable next Tuesday", and
  vacation ranges. The epic asks for a recurring weekly pattern, and a diary of exceptions is only
  meaningful against a calendar of events.
- **Time zones**: stated times are wall-clock times read the same way by everyone, per the assumption
  below. Multi-region trainers and per-user time zones are not addressed.
- **Trainer-side management of a coach's profile**: a trainer reads their coaches and can end an
  assignment; editing a coach's bio, credentials, or certifications remains the coach's own, as feature
  001 established for every account's own profile.
- **Coach visibility of anyone else's stated times**, and any coach-facing roster or player list. A
  coach sees their own times and the portal of the trainer they work with; what a coach may see of a
  trainer's players belongs with the event and CRM epics that give them a reason to look.
- **Analytics over invitations or availability**: conversion rates on coach invitations, referral
  attribution, and reporting on how much availability is stated. Usage is recorded; Epic-06 reads it.
- **Impersonation of a Super Admin by a Super Admin**, under any justification or approval workflow.
  The rule is absolute rather than gated.
- **Consent, notification, or opt-out for the impersonated person**, and any impersonation initiated at
  a user's request through a support code. Impersonation here is an administrative act, made
  accountable by an unforgeable record rather than by the person's permission.
- **A read-only impersonation mode**, distinct from the one specified. There is one mode: the admin can
  do what the person can do, minus the account-takeover actions FR-047 forbids, and every change is
  attributed to both.
- **Sessions, roles, profiles, player invitation links, family accounts, branding, and the parent
  approval workflow**, all specified and delivered by feature `001-user-roles-admin`. This feature adds
  to that foundation and changes none of it.
- Everything Epic-01 section 4 lists as Post-MVP, including social sign-in, two-factor authentication,
  per-user permission customization, custom roles, and bulk import or export.

## Assumptions

Where Epic-01 leaves a choice open, this specification takes the following positions. Each is a default
that can be revised without restructuring the feature.

- **A coach joins as Active, with no second confirmation**: US-01.08 offers status "Pending or Active"
  on acceptance. A trainer who has typed a coach's address and sent them a personal invitation has
  already made the decision a pending state would ask them to make again, so acceptance places the
  coach on the roster immediately (FR-017). A separate approval step could be added later without
  changing anything else.
- **The invitation is bound to the address it was sent to** (FR-013). A single-use invitation addressed
  to one person that any signed-in coach could redeem would not be single-use in any meaningful sense.
  The cost is that a coach whose account sits at a different address must be re-invited at that
  address, which the refusal message tells them.
- **A trainer can end a coach's assignment** (FR-021), which US-01.08 does not mention. Without it the
  one-trainer-per-coach rule makes the first assignment permanent and a coach could never change
  employer — a dead end the platform cannot ship. Ending an assignment is the trainer's act here;
  whether a coach may leave on their own is left to the epic that gives coaches more autonomy.
- **Coach invitations expire in seven days and admit one person once**, exactly as the epic states, and
  are a distinct kind of invitation from the never-expiring standing player link of feature 001.
- **Stated times are a recurring weekly pattern on quarter-hour boundaries, at most six ranges per
  day** (FR-028). The epic asks for "hourly blocks or custom ranges"; quarter-hours accommodate both
  and match how sessions are scheduled in practice. The ceiling exists so no view renders an unbounded
  list.
- **Times are wall-clock and time-zone-free**, on the assumption that a trainer's organization and its
  families share a locale. Introducing time zones later changes how times are stored and displayed, not
  who may state or read them.
- **One stated week per person, shared by every trainer they train with** (FR-031). A player training
  with three trainers is available at the times they are available; per-trainer weeks would ask the
  family to maintain the same information three times.
- **Availability is guidance and never a constraint** (FR-038), which is the epic's own rule: "used for
  scheduling suggestions, not restrictions".
- **A child with a sign-in may state their own times.** Feature 001 FR-131 already lets a child update
  their own preferences, and times are a preference rather than a commitment; the parent retains
  authority to see and revise them (FR-033).
- **Impersonation permits action, not takeover.** The epic's requirement that actions during
  impersonation be logged with the admin's identity implies the admin can act, which is what makes the
  tool useful for support. The line drawn is account takeover: credentials, account destruction, and
  nested impersonation are refused (FR-047). Financial actions are absent because Epic-05 does not
  exist yet, not as a stated exception.
- **Inactive accounts may be impersonated; erased accounts may not.** Seeing what a deactivated person
  sees is a legitimate support question; an erased account has no personal information left to support.
- **The impersonated person is not notified.** The record is the accountability mechanism, and it is
  auditable by any Super Admin at any time.
- **One hour is the impersonation ceiling**, as the epic states, measured from the start and not
  extended by activity.
- **Email delivery and the existing session, audit, and profile-switching mechanisms of feature 001 are
  available and unchanged**; this feature adds no new external dependency.

## Dependencies

- **Feature `001-user-roles-admin`**, implemented: the four roles and three account states, sign-in and
  sessions, request-time permission enforcement (001 FR-015), the navigation frame (001 FR-062), the
  invitation-link mechanism and its kinds (001 FR-065 onward), player profiles and the family profile
  switcher (001 FR-106 onward), trainer portal branding, and the append-only audit trail (001 FR-054,
  FR-055).
- **Transactional email**, already relied upon by feature 001, to deliver coach invitations.
- **Epic-02 (Event Management)** depends on this feature: the coach-to-event conflict warning and the
  roster-wide availability filter both read the stated times delivered here.
- **Epic-03 (CRM)** depends on the player-side stated times for the player card and availability
  filtering.
