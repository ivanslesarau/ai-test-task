# Specification Quality Checklist: User Roles, Super Admin Management, ShareLink Onboarding & Portal Branding

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-19
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — **resolved in Phase 0 research**
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`

### Validation record

Validated by scanning the written spec for technology terms, mandatory sections, and requirement
coverage. One change was made as a result: the entity **Credential Setup Token** was renamed
**Credential Setup Invitation**, because "token" was the only term in the document that read as an
implementation mechanism rather than a business concept. A rescan found no remaining technology
references.

Coverage counts at time of validation: 56 functional requirements, 12 success criteria, 46
Given/When/Then acceptance scenarios across 5 user stories, plus 11 edge cases.

**Revalidated 2026-08-25** after the bug-fix slice's approved amendments: **64 functional
requirements and 14 success criteria**. FR-057 to FR-064 and SC-013 to SC-014 were added to give the
six reported post-implementation defects requirement backing, as Principle I requires. All 16
checklist items were re-scanned and still pass — the new requirements name no library, endpoint, or
file layout, and each is measurable through SC-013, SC-014, or an existing acceptance scenario. The
technical decisions they rest on live in `plan.md` §Post-Implementation Technical Decisions
(D-01 to D-06), not in the specification.

Every functional requirement traces to at least one acceptance scenario or success criterion, and
each of the four requested epic stories maps to a user story here:

| Epic story | User story in this spec | Requirements |
|------------|-------------------------|--------------|
| Foundation (roles, statuses, profiles) | US1 — Role-Separated Sign-In | FR-001 – FR-020 |
| US-01.01 Super Admin creates trainer | US2 — Super Admin Creates a Trainer Account | FR-021 – FR-030 |
| US-01.11 User edits own profile | US3 — Any User Edits Their Own Profile | FR-031 – FR-036 |
| US-01.12 Super Admin deactivates user | US4 — Deactivates and Reactivates a User | FR-037 – FR-042 |
| US-01.13 Super Admin deletes user (GDPR) | US5 — Erases a User's Personal Information | FR-043 – FR-050 |

Supporting requirements FR-051 – FR-056 cover the user directory the Super Admin stories act
through, and the audit trail all four stories write to.

### Clarifications resolved (2)

Both markers were raised with the user, then resolved during Phase 0 of `/speckit-plan` and written
back into the requirements they affected. Full reasoning and rejected alternatives are in
[research.md](../research.md) R-01 and R-02.

| Was | Requirement | Resolution |
|-----|-------------|------------|
| Setup link, temporary password, or both? | FR-025 | Single-use setup link expiring after 24 hours; no password in the email |
| Which roles may a Super Admin assign? | FR-030 | Any of the four; created accounts carry no organizational relationships |

FR-030's resolution also added acceptance scenario 9 to US2 and revised the Assumptions note on
roles needed for testing.

**Checklist status (2026-08-25): all 16 items pass.**

**Revalidated 2026-08-26** after the ShareLink and portal-branding extension: **104 functional
requirements, 25 success criteria, 70 Given/When/Then acceptance scenarios across 8 user stories,
and 25 edge cases**. User Stories 6 to 8, FR-065 to FR-104, SC-015 to SC-025, four key entities
(Invitation Link, Trainer–Player Association, Active Trainer Context, Trainer Portal Branding), and
14 edge cases were added to cover epic stories US-01.02 and US-01.14 plus the multi-trainer
association the user called out. The Out of Scope section was rewritten accordingly: the three
bullets that previously excluded ShareLink registration, multi-trainer associations, and portal
branding were removed, and six bullets were added to fence what remains excluded (child-profile
family selection, coach invitation links, link analytics, trainer-side association management, and
Phase 2 branding).

All 16 checklist items were re-scanned against the extended document and still pass:

| Item | Evidence |
|------|----------|
| No implementation details | A term scan over the new text found no library, endpoint, storage, or file-layout reference. "Invitation link" and "code" are business concepts; the epic's own name "ShareLink" is kept only in headings and the scope note so the epic can be traced. |
| Requirements testable | Each of FR-065 to FR-104 names an observable outcome; the ones that are hard to observe directly (FR-066 unguessability, FR-090 cross-trainer disclosure, FR-099 legibility) are pinned to SC-021, SC-025, and SC-023 respectively. |
| Success criteria measurable and technology-agnostic | SC-015 to SC-025 state times, counts, percentages, and a contrast ratio. None names a technology; the 4.5:1 ratio is an accessibility measure, not an implementation. |
| Acceptance scenarios defined | 23 new scenarios: 7 for Story 6, 8 for Story 7, 8 for Story 8. |
| Edge cases identified | 14 new edge cases covering dead links, wrong-role visitors, racing registrations, revocation, code guessing, erased players on rosters, a vanishing active trainer, players with no trainer, cross-trainer disclosure, logo replacement, unreadable colours, active content in vector uploads, and branding reaching people already signed in. |
| Scope bounded | Out of Scope rewritten as described above; the multi-trainer selection prompt and coach links are explicitly deferred with the reason and the story that owns them. |
| Dependencies and assumptions identified | Ten new assumptions recorded under "Assumptions added with the 2026-08-26 extension". |

Story-to-requirement mapping for the extension:

| Epic story | User story in this spec | Requirements |
|------------|-------------------------|--------------|
| US-01.02 Player registers via ShareLink | US6 — Joins a Trainer Through an Invitation Link | FR-065 – FR-083 |
| US-01.02 (Multi-Trainer) + separated views | US7 — Trains With Several Trainers | FR-084 – FR-092 |
| US-01.14 Trainer customizes portal branding | US8 — Puts Their Own Brand on Their Portal | FR-093 – FR-104 |

Two wording decisions were made rather than raised as clarifications, because the epic settles both
and no reasonable alternative reading survives it:

- The request named US-01.14 "coach portal customization". Epic-01 §US-01.14 assigns the
  customization to the **Trainer**, whose branding coaches and players then see. The spec follows the
  epic: FR-093 gives the trainer the settings and denies them to coaches, and FR-101 makes coaches
  part of the audience.
- The request said a player can be associated with multiple **coaches**. Epic-01 states a coach works
  for exactly one trainer and that it is **trainers** a player may hold several of. The spec
  implements multi-**trainer** association (FR-084) and leaves the one-trainer-per-coach rule out of
  scope with US-01.08.

**Checklist status (2026-08-26): all 16 items pass.**

