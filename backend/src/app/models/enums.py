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
