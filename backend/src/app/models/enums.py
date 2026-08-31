from enum import StrEnum


class UserRole(StrEnum):
    """Exactly four roles, closed set (FR-002). A fifth is a schema change."""

    SUPER_ADMIN = "super_admin"
    TRAINER = "trainer"
    COACH = "coach"
    PLAYER_PARENT = "player_parent"


class AccountStatus(StrEnum):
    """Three lifecycle states (FR-003). DELETED is terminal."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


# Permitted transitions (data-model.md §1, FR-003). Any pair not listed here
# — including a status "transitioning" to itself — is a domain error.
ALLOWED_STATUS_TRANSITIONS: frozenset[tuple[AccountStatus, AccountStatus]] = frozenset(
    {
        (AccountStatus.ACTIVE, AccountStatus.INACTIVE),
        (AccountStatus.INACTIVE, AccountStatus.ACTIVE),
        (AccountStatus.ACTIVE, AccountStatus.DELETED),
        (AccountStatus.INACTIVE, AccountStatus.DELETED),
    }
)


def is_transition_allowed(current: AccountStatus, target: AccountStatus) -> bool:
    return (current, target) in ALLOWED_STATUS_TRANSITIONS


class ShareLinkKind(StrEnum):
    """Only PLAYER_STANDING is ever issued (FR-072). Coach invitations do
    NOT use this table or this enum: they live in their own
    `coach_invitations` table (`app.models.coach_invitation`), because the
    two secrets have opposite security postures and opposite disclosure
    rules (data-model.md §109.4, research.md R2-01). A `COACH_SINGLE_USE`
    member used to be declared here as a forward reference for US-01.08;
    it is removed now that US-01.08 has chosen a dedicated table instead —
    no row of that kind was ever written."""

    PLAYER_STANDING = "player_standing"


class AssociationStatus(StrEnum):
    """ACTIVE means the player trains with the trainer and appears in the
    switcher. Nothing in this feature sets INACTIVE — that is US-01.04."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class Gender(StrEnum):
    """Closed set (research.md R-32) so later epics can group and filter
    by it, matching how UserRole and AccountStatus are persisted."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class PlayerProfileKind(StrEnum):
    """Which kind of player a profile describes (data-model.md §25, FR-106).

    SELF is the account holder training themselves — at most one per
    account, enforced by a partial unique index — and its name and photo
    are read from `user_profiles` rather than stored again on the profile
    (research.md R-37). CHILD is a player the account holder is
    responsible for; any number per account, and it carries its own name
    because a child without a sign-in has no `users` row to read from.
    """

    SELF = "self"
    CHILD = "child"


class ApprovalRequestKind(StrEnum):
    """What a child is asking their parent to allow (FR-142).

    Only JOIN_TRAINER is created and executed by this feature — it is the
    one kind whose subject exists in the platform today. USD_PAYMENT and
    TOKEN_SPEND carry their rules and their recorded shape here, and their
    execution belongs to Epic-05: no executor is registered for them, so
    approving one raises rather than recording an approval whose action
    never happened (research.md R-46).
    """

    JOIN_TRAINER = "join_trainer"
    USD_PAYMENT = "usd_payment"
    TOKEN_SPEND = "token_spend"


class ApprovalRequestStatus(StrEnum):
    """The states an approval request passes through (FR-143).

    PENDING_PARENT_APPROVAL and INFO_REQUESTED are live; the other four
    are terminal. Only APPROVED permits the requested action to happen,
    and it happens exactly once (FR-144). EXPIRED is distinguished from
    DENIED so a parent who never saw a request stays distinguishable in
    the record from one who considered it and said no (research.md R-43).
    """

    PENDING_PARENT_APPROVAL = "pending_parent_approval"
    INFO_REQUESTED = "info_requested"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


LIVE_APPROVAL_STATUSES: frozenset[ApprovalRequestStatus] = frozenset(
    {
        ApprovalRequestStatus.PENDING_PARENT_APPROVAL,
        ApprovalRequestStatus.INFO_REQUESTED,
    }
)

# Permitted transitions (data-model.md §25, FR-143). Any pair not listed
# here is a domain error. Note the deliberate absence of
# INFO_REQUESTED -> APPROVED: the parent asked a question, so the child's
# answer returns the request to pending and the parent decides from there.
ALLOWED_APPROVAL_TRANSITIONS: frozenset[tuple[ApprovalRequestStatus, ApprovalRequestStatus]] = (
    frozenset(
        {
            (ApprovalRequestStatus.PENDING_PARENT_APPROVAL, ApprovalRequestStatus.INFO_REQUESTED),
            (ApprovalRequestStatus.PENDING_PARENT_APPROVAL, ApprovalRequestStatus.APPROVED),
            (ApprovalRequestStatus.PENDING_PARENT_APPROVAL, ApprovalRequestStatus.DENIED),
            (ApprovalRequestStatus.PENDING_PARENT_APPROVAL, ApprovalRequestStatus.EXPIRED),
            (ApprovalRequestStatus.PENDING_PARENT_APPROVAL, ApprovalRequestStatus.WITHDRAWN),
            (ApprovalRequestStatus.INFO_REQUESTED, ApprovalRequestStatus.PENDING_PARENT_APPROVAL),
            (ApprovalRequestStatus.INFO_REQUESTED, ApprovalRequestStatus.DENIED),
            (ApprovalRequestStatus.INFO_REQUESTED, ApprovalRequestStatus.EXPIRED),
            (ApprovalRequestStatus.INFO_REQUESTED, ApprovalRequestStatus.WITHDRAWN),
        }
    )
)


def is_approval_transition_allowed(
    current: ApprovalRequestStatus, target: ApprovalRequestStatus
) -> bool:
    return (current, target) in ALLOWED_APPROVAL_TRANSITIONS


# --- Extension (2026-08-28): coach invitations, availability, impersonation


class CoachInvitationState(StrEnum):
    """The four **event-driven** states a coach invitation stores
    (data-model.md §109.1, research.md R2-03). `expired` is deliberately
    absent — it is derived at read time from `expires_at` when the state
    is AWAITING, because there is no scheduler to write it. `blocked` is
    also absent — it is a pair of nullable columns
    (`blocked_at`/`blocked_reason`) on a row that stays AWAITING, so a
    refused acceptance does not spend the invitation (FR-015)."""

    AWAITING = "awaiting"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


# Permitted transitions (data-model.md §109.1). Nothing leaves a terminal
# state, and there is no AWAITING -> AWAITING self-transition: setting or
# clearing a block writes blocked_at/blocked_reason without touching state.
ALLOWED_COACH_INVITATION_TRANSITIONS: frozenset[
    tuple[CoachInvitationState, CoachInvitationState]
] = frozenset(
    {
        (CoachInvitationState.AWAITING, CoachInvitationState.ACCEPTED),
        (CoachInvitationState.AWAITING, CoachInvitationState.REVOKED),
        (CoachInvitationState.AWAITING, CoachInvitationState.SUPERSEDED),
    }
)


def is_coach_invitation_transition_allowed(
    current: CoachInvitationState, target: CoachInvitationState
) -> bool:
    return (current, target) in ALLOWED_COACH_INVITATION_TRANSITIONS


class CoachInvitationBlockReason(StrEnum):
    """Why an acceptance was refused without spending the invitation
    (data-model.md §109.2). Two values only, because FR-019 requires the
    trainer to learn *that* acceptance was blocked while learning nothing
    about the other trainer — the reason shown is a fixed phrase per
    value, and the other trainer's identity is never stored here."""

    ROLE_NOT_COACH = "role_not_coach"
    ALREADY_ASSIGNED = "already_assigned"


class ImpersonationEndReason(StrEnum):
    """Why an impersonation session ended (data-model.md §109.3, FR-045 –
    FR-050). The first two are enforced at request time in `get_principal`
    (research.md R2-19); the rest are written by the action that caused
    them."""

    EXITED = "exited"
    TIMED_OUT = "timed_out"
    SIGNED_OUT = "signed_out"
    SUPERSEDED = "superseded"
    TARGET_DEACTIVATED = "target_deactivated"
    TARGET_ERASED = "target_erased"
    ADMIN_DEACTIVATED = "admin_deactivated"
