from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid, utcnow
from app.models.association import TrainerPlayerAssociation
from app.models.enums import AssociationStatus
from app.models.role_details import PlayerDetail
from app.models.user import User, UserProfile


@dataclass
class TrainerRosterRow:
    association: TrainerPlayerAssociation
    player_user: User
    player_profile: UserProfile
    player_detail: PlayerDetail | None


class AssociationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, *, trainer_user_id: str, player_user_id: str
    ) -> TrainerPlayerAssociation | None:
        result = await self._session.execute(
            select(TrainerPlayerAssociation).where(
                TrainerPlayerAssociation.trainer_user_id == trainer_user_id,
                TrainerPlayerAssociation.player_user_id == player_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def insert(
        self, *, trainer_user_id: str, player_user_id: str, share_link_id: str | None
    ) -> TrainerPlayerAssociation:
        """Raises sqlalchemy.exc.IntegrityError on the unique
        (trainer_user_id, player_user_id) pair — the caller must check
        `get()` first under this codebase's established check-then-insert
        convention (see UserAdminService.create_user); this method does
        not catch the race itself."""
        record = TrainerPlayerAssociation(
            id=new_uuid(),
            trainer_user_id=trainer_user_id,
            player_user_id=player_user_id,
            share_link_id=share_link_id,
            status=AssociationStatus.ACTIVE.value,
            joined_at=utcnow(),
            updated_at=utcnow(),
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_active_for_player(
        self, player_user_id: str
    ) -> list[tuple[TrainerPlayerAssociation, User, UserProfile]]:
        """Only Active associations whose trainer account is Active
        (FR-089) — every row this returns is switchable."""
        rows = await self._session.execute(
            select(TrainerPlayerAssociation, User, UserProfile)
            .join(User, User.id == TrainerPlayerAssociation.trainer_user_id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(
                TrainerPlayerAssociation.player_user_id == player_user_id,
                TrainerPlayerAssociation.status == AssociationStatus.ACTIVE.value,
                User.status == "active",
            )
        )
        return [(a, u, p) for a, u, p in rows.all()]

    async def list_for_trainer(
        self,
        trainer_user_id: str,
        *,
        page: int,
        page_size: int,
        query: str | None,
    ) -> tuple[list[TrainerRosterRow], int]:
        base = (
            select(TrainerPlayerAssociation, User, UserProfile, PlayerDetail)
            .join(User, User.id == TrainerPlayerAssociation.player_user_id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .outerjoin(PlayerDetail, PlayerDetail.user_id == User.id)
            .where(
                TrainerPlayerAssociation.trainer_user_id == trainer_user_id,
                TrainerPlayerAssociation.status == AssociationStatus.ACTIVE.value,
            )
        )

        if query:
            pattern = f"%{query.lower()}%"
            base = base.where(
                or_(
                    func.lower(UserProfile.first_name).like(pattern),
                    func.lower(UserProfile.last_name).like(pattern),
                    func.lower(PlayerDetail.player_name).like(pattern),
                )
            )

        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()

        rows = await self._session.execute(
            base.order_by(TrainerPlayerAssociation.joined_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [
            TrainerRosterRow(association=a, player_user=u, player_profile=p, player_detail=d)
            for a, u, p, d in rows.all()
        ], total

    async def count_for_trainer(self, trainer_user_id: str) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                TrainerPlayerAssociation.trainer_user_id == trainer_user_id,
                TrainerPlayerAssociation.status == AssociationStatus.ACTIVE.value,
            )
        )
        return result.scalar_one()
