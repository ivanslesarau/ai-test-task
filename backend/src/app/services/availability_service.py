"""`/me/availability`, `/me/players/{profile_id}/availability`, and
(US5, T606) `/trainer/players/{profile_id}/availability` — one weekly
pattern of stated ranges, for either owner kind (research.md R2-07,
data-model.md §111.2, tasks.md T574).

For the owner's own reads and writes, authorization is NOT this service's
job: `/me/availability` is Coach-only by the router's own role gate, and
`/me/players/{profile_id}/availability` resolves ownership through
`FamilyService`'s existing reachability check before this service is ever
called (research.md R2-11) — nesting under a resource that already owns
its authorization matrix, rather than building a second one here.

The one exception is `get_week_for_profile_as_trainer` (US5): there is no
existing single-profile trainer-side resource to nest under, so this
method performs its own scoping query — an Active
`trainer_player_associations` row — exactly as `data-model.md §113`
describes, raising `NotFound` (never `PermissionDenied`) for anyone else's
profile or a lapsed association.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.availability_rules import MAX_SLOTS_PER_DAY, MINUTES_IN_DAY, MINUTES_PER_SLOT_STEP
from app.core.errors import NotFound, ValidationFailure
from app.db.base import new_uuid, utcnow
from app.models.availability import AvailabilitySlot
from app.models.enums import AssociationStatus
from app.repositories.association_repository import AssociationRepository
from app.repositories.availability_repository import AvailabilityRepository
from app.schemas.availability import (
    AvailabilitySlotModel,
    AvailabilityWeekOut,
    AvailabilityWeekUpdate,
)

_DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class SlotLike(Protocol):
    """The three ints `validate_week` needs — satisfied structurally by
    `AvailabilitySlotModel` (the real request path) and by any lightweight
    test double (`backend/tests/unit/test_availability_validation.py`),
    with no inheritance required."""

    day_of_week: int
    start_minute: int
    end_minute: int


def _day_label(day_of_week: int) -> str:
    if 0 <= day_of_week < len(_DAY_NAMES):
        return _DAY_NAMES[day_of_week]
    return f"day {day_of_week}"


def validate_week(slots: Sequence[SlotLike]) -> None:
    """The whole-week validator (data-model.md §111.2): validates the
    entire submitted week before a single row is touched, raising
    `ValidationFailure` keyed by the offending day (FR-027) — the field
    key is `str(day_of_week)`, which the frontend maps back onto the
    editor's own per-day state.

    Re-checks grid/order/bounds independently of `AvailabilitySlotModel`'s
    own Pydantic constraints — belt-and-suspenders exactly like the
    database's `ck_availability_slots_*` CHECKs duplicate the same rules
    (data-model.md §103), and what makes this function directly
    unit-testable with values Pydantic would already have refused at the
    API boundary.

    In order: 1) every slot's own shape (grid, bounds, start < end);
    2) at most `MAX_SLOTS_PER_DAY` a day (FR-028); 3) no two slots on one
    day overlap — sorted by `start_minute`, an overlap is
    `next.start < previous.end`; touching ranges (`next.start ==
    previous.end`) are valid (FR-027's explicit edge case).
    """
    by_day: dict[int, list[SlotLike]] = {}
    for slot in slots:
        by_day.setdefault(slot.day_of_week, []).append(slot)

    for day, day_slots in by_day.items():
        label = _day_label(day)
        field = str(day)

        for slot in day_slots:
            if slot.start_minute % MINUTES_PER_SLOT_STEP != 0 or (
                slot.end_minute % MINUTES_PER_SLOT_STEP != 0
            ):
                raise ValidationFailure(
                    f"{label}: times must fall on a {MINUTES_PER_SLOT_STEP}-minute grid.",
                    fields={field: f"Times must fall on a {MINUTES_PER_SLOT_STEP}-minute grid."},
                )
            if not (0 <= slot.start_minute < slot.end_minute <= MINUTES_IN_DAY):
                raise ValidationFailure(
                    f"{label}: a range must start before it ends and stay within the day.",
                    fields={field: "A range must start before it ends and stay within the day."},
                )

        if len(day_slots) > MAX_SLOTS_PER_DAY:
            raise ValidationFailure(
                f"{label}: no more than {MAX_SLOTS_PER_DAY} ranges are allowed in a day.",
                fields={field: f"No more than {MAX_SLOTS_PER_DAY} ranges are allowed in a day."},
            )

        ordered = sorted(day_slots, key=lambda s: s.start_minute)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if current.start_minute < previous.end_minute:
                raise ValidationFailure(
                    f"{label}: ranges overlap.",
                    fields={field: "Ranges on this day overlap."},
                )


def _assert_one_owner(coach_user_id: str | None, profile_id: str | None) -> None:
    assert (coach_user_id is None) != (profile_id is None), "exactly one owner must be given"


class AvailabilityService:
    """One service for both owner kinds (research.md R2-07) — every
    method takes `coach_user_id` XOR `profile_id`, mirroring
    `ck_availability_slots_one_owner`."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._repo = AvailabilityRepository(db_session)
        self._associations = AssociationRepository(db_session)

    async def get_week_for_profile_as_trainer(
        self, *, trainer_user_id: str, profile_id: str
    ) -> AvailabilityWeekOut:
        """US5 (T606): a trainer's read of a player profile's stated week
        (FR-034, FR-036, FR-037), scoped to an **Active** association
        between the caller and this profile — the same query that
        authorizes the read is the one that would stop matching the
        moment the association ends, so disclosure stops immediately
        with no separate step (FR-039, research.md R2-11, data-model.md
        §113). An unreachable profile — no association, or one that is
        not Active — is a 404, never a 403: the caller is naming a
        resource they do not have."""
        association = await self._associations.get(
            trainer_user_id=trainer_user_id, player_profile_id=profile_id
        )
        if association is None or association.status != AssociationStatus.ACTIVE.value:
            raise NotFound("No such player.")
        return await self.get_week(profile_id=profile_id)

    async def get_week(
        self, *, coach_user_id: str | None = None, profile_id: str | None = None
    ) -> AvailabilityWeekOut:
        _assert_one_owner(coach_user_id, profile_id)
        rows = (
            await self._repo.list_for_coach(coach_user_id)
            if coach_user_id is not None
            else await self._repo.list_for_profile(profile_id)  # type: ignore[arg-type]
        )
        updated_at = await self._repo.get_updated_at(
            coach_user_id=coach_user_id, profile_id=profile_id
        )
        return AvailabilityWeekOut(
            slots=[self._to_slot_model(row) for row in rows], updated_at=updated_at
        )

    async def replace_week(
        self,
        update: AvailabilityWeekUpdate,
        *,
        coach_user_id: str | None = None,
        profile_id: str | None = None,
    ) -> AvailabilityWeekOut:
        """FR-029, research.md R2-10: validates the entire submitted week
        first — nothing is written if any part is refused (FR-027) — then
        deletes every existing row for the owner, inserts the new set, and
        stamps `availability_updated_at`, all inside the request's single
        transaction (the session commits once, at `get_db_session`
        teardown). Last complete save wins; there is no version token."""
        _assert_one_owner(coach_user_id, profile_id)
        validate_week(update.slots)

        when = utcnow()
        await self._repo.delete_for_owner(coach_user_id=coach_user_id, profile_id=profile_id)

        new_rows = [
            AvailabilitySlot(
                id=new_uuid(),
                coach_user_id=coach_user_id,
                player_profile_id=profile_id,
                day_of_week=slot.day_of_week,
                start_minute=slot.start_minute,
                end_minute=slot.end_minute,
                created_at=when,
            )
            for slot in update.slots
        ]
        if new_rows:
            await self._repo.insert_many(new_rows)
        await self._repo.stamp_updated_at(when, coach_user_id=coach_user_id, profile_id=profile_id)

        ordered = sorted(new_rows, key=lambda row: (row.day_of_week, row.start_minute))
        return AvailabilityWeekOut(
            slots=[self._to_slot_model(row) for row in ordered], updated_at=when
        )

    async def clear_week(
        self, *, coach_user_id: str | None = None, profile_id: str | None = None
    ) -> None:
        """FR-030, FR-032: equivalent to saving an empty week — `slots`
        becomes `[]` and `availability_updated_at` is stamped, so the week
        reads as cleared-on-a-date rather than never-stated (FR-035)."""
        await self.replace_week(
            AvailabilityWeekUpdate(slots=[]), coach_user_id=coach_user_id, profile_id=profile_id
        )

    @staticmethod
    def _to_slot_model(row: AvailabilitySlot) -> AvailabilitySlotModel:
        return AvailabilitySlotModel(
            day_of_week=row.day_of_week, start_minute=row.start_minute, end_minute=row.end_minute
        )
