"""Unit tests for the whole-week validator (data-model.md §111.2, FR-027,
FR-028, tasks.md T567). Pure — no database, no HTTP client. `validate_week`
is exercised directly with a lightweight local slot type so invalid
combinations (off-grid, start >= end, past-midnight) can be constructed even
though the real request path's Pydantic schema (`AvailabilitySlotModel`)
would already refuse most of them at the API boundary; this file proves the
service's own defence-in-depth copy of the same rules, independently of
Pydantic, is correct on its own terms — including that every failure names
the offending day (FR-027)."""

from dataclasses import dataclass

import pytest

from app.core.errors import ValidationFailure
from app.services.availability_service import validate_week


@dataclass(frozen=True)
class Slot:
    day_of_week: int
    start_minute: int
    end_minute: int


def test_empty_week_is_valid() -> None:
    validate_week([])


def test_a_single_valid_slot_is_accepted() -> None:
    validate_week([Slot(day_of_week=0, start_minute=540, end_minute=600)])


def test_touching_ranges_on_one_day_are_accepted() -> None:
    """FR-027's explicit edge case: `next.start == previous.end` is NOT an
    overlap."""
    validate_week(
        [
            Slot(day_of_week=2, start_minute=540, end_minute=600),
            Slot(day_of_week=2, start_minute=600, end_minute=660),
        ]
    )


def test_non_overlapping_ranges_on_different_days_are_accepted() -> None:
    validate_week(
        [
            Slot(day_of_week=0, start_minute=540, end_minute=600),
            Slot(day_of_week=1, start_minute=540, end_minute=600),
        ]
    )


def test_overlapping_ranges_on_one_day_are_refused_and_the_day_is_named() -> None:
    with pytest.raises(ValidationFailure) as exc_info:
        validate_week(
            [
                Slot(day_of_week=3, start_minute=540, end_minute=660),
                Slot(day_of_week=3, start_minute=600, end_minute=720),
            ]
        )
    assert "3" in exc_info.value.fields


def test_overlap_detection_regardless_of_submission_order() -> None:
    """The validator sorts by start_minute before checking, so an
    unordered submission is caught exactly the same as an ordered one."""
    with pytest.raises(ValidationFailure) as exc_info:
        validate_week(
            [
                Slot(day_of_week=5, start_minute=600, end_minute=720),
                Slot(day_of_week=5, start_minute=540, end_minute=660),
            ]
        )
    assert "5" in exc_info.value.fields


def test_start_at_or_after_end_is_refused_and_the_day_is_named() -> None:
    with pytest.raises(ValidationFailure) as exc_info:
        validate_week([Slot(day_of_week=1, start_minute=600, end_minute=600)])
    assert "1" in exc_info.value.fields


def test_start_after_end_is_refused() -> None:
    with pytest.raises(ValidationFailure) as exc_info:
        validate_week([Slot(day_of_week=1, start_minute=700, end_minute=600)])
    assert "1" in exc_info.value.fields


def test_a_range_past_the_end_of_the_day_is_refused_and_the_day_is_named() -> None:
    with pytest.raises(ValidationFailure) as exc_info:
        validate_week([Slot(day_of_week=6, start_minute=1425, end_minute=1470)])
    assert "6" in exc_info.value.fields


def test_a_range_ending_exactly_at_midnight_is_accepted() -> None:
    """`end_minute == 1440` is permitted — a range may finish at midnight
    (research.md R2-08)."""
    validate_week([Slot(day_of_week=6, start_minute=1380, end_minute=1440)])


def test_an_off_grid_start_is_refused_and_the_day_is_named() -> None:
    with pytest.raises(ValidationFailure) as exc_info:
        validate_week([Slot(day_of_week=4, start_minute=545, end_minute=600)])
    assert "4" in exc_info.value.fields


def test_an_off_grid_end_is_refused_and_the_day_is_named() -> None:
    with pytest.raises(ValidationFailure) as exc_info:
        validate_week([Slot(day_of_week=4, start_minute=540, end_minute=607)])
    assert "4" in exc_info.value.fields


def test_seven_ranges_in_one_day_is_refused_and_the_day_is_named() -> None:
    slots = [Slot(day_of_week=0, start_minute=i * 60, end_minute=i * 60 + 30) for i in range(7)]
    with pytest.raises(ValidationFailure) as exc_info:
        validate_week(slots)
    assert "0" in exc_info.value.fields


def test_exactly_six_ranges_in_one_day_is_accepted() -> None:
    slots = [Slot(day_of_week=0, start_minute=i * 60, end_minute=i * 60 + 30) for i in range(6)]
    validate_week(slots)


def test_a_negative_start_minute_is_refused() -> None:
    with pytest.raises(ValidationFailure) as exc_info:
        validate_week([Slot(day_of_week=2, start_minute=-15, end_minute=60)])
    assert "2" in exc_info.value.fields
