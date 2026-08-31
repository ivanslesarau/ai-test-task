"""A trainer's coach roster: read and end an assignment (US2, FR-020 –
FR-023). Authorization is scoped by the same query that selects the data
— `list_coaches_for_trainer`'s `WHERE coach_details.trainer_user_id = ?`
and `end_assignment`'s ownership check — so there is no separate
permission matrix to keep in sync (research.md R2-11's pattern, reused
here for the trainer's own side of the relationship).
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.availability_repository import AvailabilityRepository
from app.repositories.user_repository import UserRepository
from app.schemas.availability import AvailabilitySlotModel, AvailabilityWeekOut
from app.schemas.coach import TrainerCoachPage, TrainerCoachSummary


class CoachService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._users = UserRepository(db_session)
        self._availability = AvailabilityRepository(db_session)
        self._audit = AuditRepository(db_session)

    async def list_roster(
        self, trainer_user_id: str, *, page: int, page_size: int, query: str | None
    ) -> TrainerCoachPage:
        """FR-020, FR-034, FR-036: scoped to the caller's own roster, with
        no parameter that could widen it. Each row carries its stated
        week from one `IN` query for the whole page (research.md R2-12),
        never one request per row."""
        rows, total = await self._users.list_coaches_for_trainer(
            trainer_user_id, page=page, page_size=page_size, query=query
        )
        slots_by_coach = await self._availability.list_for_coaches([user.id for user, _, _ in rows])

        items = [
            TrainerCoachSummary(
                user_id=user.id,
                first_name=profile.first_name,
                last_name=profile.last_name,
                email=user.email,
                status=user.status_enum.value,  # type: ignore[arg-type]
                photo_url=f"/media/photos/{profile.photo_key}" if profile.photo_key else None,
                joined_at=_require_joined_at(detail.joined_at),
                availability=[
                    AvailabilitySlotModel(
                        day_of_week=slot.day_of_week,
                        start_minute=slot.start_minute,
                        end_minute=slot.end_minute,
                    )
                    for slot in slots_by_coach.get(user.id, [])
                ],
                availability_updated_at=detail.availability_updated_at,
            )
            for user, profile, detail in rows
        ]
        return TrainerCoachPage(items=items, total=total, page=page, page_size=page_size)

    async def get_availability_for_trainer(
        self, trainer_user_id: str, coach_user_id: str
    ) -> AvailabilityWeekOut:
        """US5 (T606), FR-034, FR-036, FR-037: a trainer's read-only view
        of a coach's stated week, scoped by the same ownership check
        `end_assignment` already uses — a coach on another trainer's
        roster, or on none, is 404, never 403 (research.md R2-11)."""
        detail = await self._users.get_coach_detail(coach_user_id)
        if detail is None or detail.trainer_user_id != trainer_user_id:
            raise NotFound("No such coach.")
        slots = await self._availability.list_for_coach(coach_user_id)
        return AvailabilityWeekOut(
            slots=[
                AvailabilitySlotModel(
                    day_of_week=slot.day_of_week,
                    start_minute=slot.start_minute,
                    end_minute=slot.end_minute,
                )
                for slot in slots
            ],
            updated_at=detail.availability_updated_at,
        )

    async def end_assignment(self, trainer: User, coach_user_id: str) -> None:
        """FR-021 – FR-023: the coach is on no roster afterwards, reaches
        none of this trainer's data, keeps their own account, profile,
        and stated times, and is free to accept another trainer's
        invitation. A coach not on this trainer's roster is a 404 — the
        caller is naming a resource they do not have."""
        detail = await self._users.get_coach_detail(coach_user_id)
        if detail is None or detail.trainer_user_id != trainer.id:
            raise NotFound("No such coach.")
        await self._users.end_coach_assignment(detail)
        await self._audit.add(
            action="coach_assignment_ended",
            actor_user_id=trainer.id,
            target_user_id=coach_user_id,
            detail=f"trainer={trainer.id}",
        )


def _require_joined_at(joined_at: datetime | None) -> datetime:
    """`ck_coach_details_assignment_pair` guarantees `joined_at` is set
    whenever `trainer_user_id` is — which is exactly the rows
    `list_coaches_for_trainer` selects — so this is an invariant check,
    not a null-coalesce."""
    assert joined_at is not None, "a roster row must carry a join date"
    return joined_at
