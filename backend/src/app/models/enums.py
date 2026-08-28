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
    """Only PLAYER_STANDING is issued by this feature (FR-072). The
    single-use coach variety is declared so US-01.08 is additive rather
    than a restructuring — no row of that kind exists yet."""

    PLAYER_STANDING = "player_standing"
    COACH_SINGLE_USE = "coach_single_use"


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
