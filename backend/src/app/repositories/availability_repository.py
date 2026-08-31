from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability import AvailabilitySlot
from app.models.player_profile import PlayerProfile
from app.models.role_details import CoachDetail


class AvailabilityRepository:
    """Queries only (data-model.md §103, §104, §113, T572) — the
    whole-week validator, the atomic replace, and every authorization
    decision belong to `AvailabilityService`, never here (Principle III).

    Every write method takes the owner as `coach_user_id` XOR
    `profile_id`, mirroring `ck_availability_slots_one_owner` — the two
    kinds share one table and one repository (research.md R2-07)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- reads --------------------------------------------------------------

    async def list_for_coach(self, coach_user_id: str) -> list[AvailabilitySlot]:
        result = await self._session.execute(
            select(AvailabilitySlot)
            .where(AvailabilitySlot.coach_user_id == coach_user_id)
            .order_by(AvailabilitySlot.day_of_week, AvailabilitySlot.start_minute)
        )
        return list(result.scalars().all())

    async def list_for_profile(self, profile_id: str) -> list[AvailabilitySlot]:
        result = await self._session.execute(
            select(AvailabilitySlot)
            .where(AvailabilitySlot.player_profile_id == profile_id)
            .order_by(AvailabilitySlot.day_of_week, AvailabilitySlot.start_minute)
        )
        return list(result.scalars().all())

    async def list_for_coaches(
        self, coach_user_ids: Sequence[str]
    ) -> dict[str, list[AvailabilitySlot]]:
        """The coach-roster twin of `list_for_profiles` (data-model.md
        §113, tasks.md T552) — one `IN` query for a whole roster page,
        never one query per coach. Every requested id is a key in the
        result, even when it holds no slots."""
        grouped: dict[str, list[AvailabilitySlot]] = {
            coach_user_id: [] for coach_user_id in coach_user_ids
        }
        if not coach_user_ids:
            return grouped
        result = await self._session.execute(
            select(AvailabilitySlot)
            .where(AvailabilitySlot.coach_user_id.in_(coach_user_ids))
            .order_by(AvailabilitySlot.day_of_week, AvailabilitySlot.start_minute)
        )
        for slot in result.scalars().all():
            assert slot.coach_user_id is not None
            grouped[slot.coach_user_id].append(slot)
        return grouped

    async def list_for_profiles(
        self, profile_ids: Sequence[str]
    ) -> dict[str, list[AvailabilitySlot]]:
        """One `IN` query for a whole roster page (data-model.md §113) —
        the N+1 this feature must not introduce. Every requested id is a
        key in the result, even when it holds no slots."""
        grouped: dict[str, list[AvailabilitySlot]] = {profile_id: [] for profile_id in profile_ids}
        if not profile_ids:
            return grouped
        result = await self._session.execute(
            select(AvailabilitySlot)
            .where(AvailabilitySlot.player_profile_id.in_(profile_ids))
            .order_by(AvailabilitySlot.day_of_week, AvailabilitySlot.start_minute)
        )
        for slot in result.scalars().all():
            assert slot.player_profile_id is not None
            grouped[slot.player_profile_id].append(slot)
        return grouped

    async def get_updated_at(
        self, *, coach_user_id: str | None = None, profile_id: str | None = None
    ) -> datetime | None:
        assert (coach_user_id is None) != (profile_id is None), "exactly one owner"
        if coach_user_id is not None:
            detail = await self._session.get(CoachDetail, coach_user_id)
            return detail.availability_updated_at if detail is not None else None
        assert profile_id is not None
        profile = await self._session.get(PlayerProfile, profile_id)
        return profile.availability_updated_at if profile is not None else None

    # --- writes ---------------------------------------------------------------

    async def delete_for_owner(
        self, *, coach_user_id: str | None = None, profile_id: str | None = None
    ) -> None:
        assert (coach_user_id is None) != (profile_id is None), "exactly one owner"
        if coach_user_id is not None:
            await self._session.execute(
                delete(AvailabilitySlot).where(AvailabilitySlot.coach_user_id == coach_user_id)
            )
        else:
            await self._session.execute(
                delete(AvailabilitySlot).where(AvailabilitySlot.player_profile_id == profile_id)
            )

    async def insert_many(self, slots: Sequence[AvailabilitySlot]) -> None:
        self._session.add_all(slots)
        await self._session.flush()

    async def stamp_updated_at(
        self,
        when: datetime,
        *,
        coach_user_id: str | None = None,
        profile_id: str | None = None,
    ) -> None:
        """The owner-timestamp write (data-model.md §104, research.md
        R2-09) — the whole reason a cleared week is distinguishable from
        one never stated. The owner row is guaranteed to exist: every
        coach account gets a `coach_details` row at creation, and every
        `player_profiles` row is the thing being addressed."""
        assert (coach_user_id is None) != (profile_id is None), "exactly one owner"
        if coach_user_id is not None:
            detail = await self._session.get(CoachDetail, coach_user_id)
            assert detail is not None
            detail.availability_updated_at = when
        else:
            assert profile_id is not None
            profile = await self._session.get(PlayerProfile, profile_id)
            assert profile is not None
            profile.availability_updated_at = when
