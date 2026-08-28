"""Pure family-profile business rules (data-model.md §26, §32; research.md
R-37, R-45). No I/O and no framework imports here — these are the rules
`backend/tests/unit/test_family_rules.py` (tasks.md T346) exercises
directly, without a database or an HTTP client, and the ones
`family_service.py` and `schemas/player_profile.py` call so the rule is
defined exactly once."""

from __future__ import annotations

from datetime import date

from app.models.enums import PlayerProfileKind


def age_on(date_of_birth: date, *, today: date) -> int:
    """Derived age, never stored (research.md R-31)."""
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years


def is_valid_age_for_kind(kind: PlayerProfileKind, age: int) -> bool:
    """FR-108: a `self` profile's derived age must be at least 18; a
    `child` profile's must be between 1 and 18 inclusive."""
    if kind is PlayerProfileKind.SELF:
        return age >= 18
    return 1 <= age <= 18


def can_create_self_profile(existing_kinds: list[str]) -> bool:
    """FR-106: at most one `self` profile per account. This documents, and
    is tested against, the same rule `uq_player_profiles_one_self`
    enforces by construction in the database — the partial unique index
    is what actually makes concurrent creation safe (Story 9 scenario 8),
    but the rule itself is the one this function states. No endpoint in
    this phase creates a `self` profile (`CreateChildProfileRequest`
    carries no `kind` field — the account holder's own profile is created
    at registration), so this is not yet called from `family_service`;
    kept for the invariant's own testability (tasks.md T346) and for the
    endpoint that will create one."""
    return PlayerProfileKind.SELF.value not in existing_kinds


def self_profile_rejects_names(
    kind: PlayerProfileKind, *, has_first_name: bool, has_last_name: bool
) -> bool:
    """research.md R-37: a `self` profile's name is the account's — a
    write supplying `first_name` or `last_name` against one must be
    refused (422), not silently dropped."""
    return kind is PlayerProfileKind.SELF and (has_first_name or has_last_name)


def names_are_possible_duplicate(*, first_a: str, last_a: str, first_b: str, last_b: str) -> bool:
    """research.md R-45: same account, same date of birth (checked by the
    caller separately), and a case-insensitive, trimmed match on **both**
    names. Deliberately not fuzzy — 'Jon' and 'John' must never collide,
    so two siblings named for the same relative are never mistaken for
    the same child."""
    return (
        first_a.strip().lower() == first_b.strip().lower()
        and last_a.strip().lower() == last_b.strip().lower()
    )
