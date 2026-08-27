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
