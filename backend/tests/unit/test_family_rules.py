from datetime import date

from app.core.family_rules import (
    age_on,
    can_create_self_profile,
    is_valid_age_for_kind,
    names_are_possible_duplicate,
    self_profile_rejects_names,
)
from app.models.enums import PlayerProfileKind

_TODAY = date(2026, 8, 27)


def test_age_on_a_birthday_already_passed_this_year() -> None:
    assert age_on(date(2016, 1, 1), today=_TODAY) == 10


def test_age_on_a_birthday_not_yet_reached_this_year() -> None:
    assert age_on(date(2016, 12, 31), today=_TODAY) == 9


def test_age_on_the_exact_birthday() -> None:
    assert age_on(date(2008, 8, 27), today=_TODAY) == 18


# --- FR-108: age band by kind -----------------------------------------------


def test_self_profile_requires_at_least_eighteen() -> None:
    assert is_valid_age_for_kind(PlayerProfileKind.SELF, 18) is True
    assert is_valid_age_for_kind(PlayerProfileKind.SELF, 17) is False


def test_child_profile_requires_between_one_and_eighteen_inclusive() -> None:
    assert is_valid_age_for_kind(PlayerProfileKind.CHILD, 1) is True
    assert is_valid_age_for_kind(PlayerProfileKind.CHILD, 18) is True
    assert is_valid_age_for_kind(PlayerProfileKind.CHILD, 0) is False
    assert is_valid_age_for_kind(PlayerProfileKind.CHILD, 19) is False


# --- FR-106: at most one self profile ---------------------------------------


def test_a_self_profile_may_be_created_when_none_exists() -> None:
    assert can_create_self_profile([]) is True
    assert can_create_self_profile(["child", "child"]) is True


def test_a_second_self_profile_is_refused() -> None:
    assert can_create_self_profile(["self"]) is False
    assert can_create_self_profile(["self", "child"]) is False


# --- research.md R-37: self profile carries no name of its own -------------


def test_self_profile_rejects_a_supplied_first_or_last_name() -> None:
    assert (
        self_profile_rejects_names(PlayerProfileKind.SELF, has_first_name=True, has_last_name=False)
        is True
    )
    assert (
        self_profile_rejects_names(PlayerProfileKind.SELF, has_first_name=False, has_last_name=True)
        is True
    )


def test_self_profile_with_no_name_fields_is_not_rejected() -> None:
    assert (
        self_profile_rejects_names(
            PlayerProfileKind.SELF, has_first_name=False, has_last_name=False
        )
        is False
    )


def test_child_profile_never_rejects_name_fields() -> None:
    assert (
        self_profile_rejects_names(PlayerProfileKind.CHILD, has_first_name=True, has_last_name=True)
        is False
    )


# --- research.md R-45: near-duplicate child predicate -----------------------


def test_exact_case_insensitive_trimmed_match_is_a_duplicate() -> None:
    assert (
        names_are_possible_duplicate(
            first_a="  Jamie ", last_a="SMITH", first_b="jamie", last_b="smith"
        )
        is True
    )


def test_a_similar_but_different_first_name_is_not_a_duplicate() -> None:
    """Deliberately not fuzzy (research.md R-45) — siblings named for the
    same relative must never collide."""
    assert (
        names_are_possible_duplicate(first_a="Jon", last_a="Smith", first_b="John", last_b="Smith")
        is False
    )


def test_a_different_last_name_is_not_a_duplicate() -> None:
    assert (
        names_are_possible_duplicate(
            first_a="Jamie", last_a="Smith", first_b="Jamie", last_b="Jones"
        )
        is False
    )
