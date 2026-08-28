from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid, utcnow
from app.models.association import TrainerPlayerAssociation
from app.models.enums import AssociationStatus
from app.models.player_profile import PlayerProfile
from app.models.role_details import ParentContact
from app.models.user import User, UserProfile


@dataclass
class TrainerRosterRow:
    """One roster row (data-model.md §35, FR-116). Carries the profile's
    own identity — never the account's — plus the account responsible for
    it: the player themselves for a SELF profile, the parent for a CHILD
    one. `responsible_account`/`responsible_profile` are the account and
    profile TrainerService reads the contact detail from; they are never
    serialized directly (FR-116, SC-040)."""

    association: TrainerPlayerAssociation
    player_profile: PlayerProfile
    responsible_account: User
    responsible_account_profile: UserProfile
    responsible_parent_contact: ParentContact | None


class AssociationRepository:
    """Queries only, at profile granularity (data-model.md §29.1, §35,
    research.md R-35). Every method joins on `player_profiles.id`, never
    on an account id — each profile's associations are wholly independent
    of every other profile's on the same account (FR-115)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, *, trainer_user_id: str, player_profile_id: str
    ) -> TrainerPlayerAssociation | None:
        result = await self._session.execute(
            select(TrainerPlayerAssociation).where(
                TrainerPlayerAssociation.trainer_user_id == trainer_user_id,
                TrainerPlayerAssociation.player_profile_id == player_profile_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, association_id: str) -> TrainerPlayerAssociation | None:
        return await self._session.get(TrainerPlayerAssociation, association_id)

    async def insert(
        self, *, trainer_user_id: str, player_profile_id: str, share_link_id: str | None
    ) -> TrainerPlayerAssociation:
        """Raises sqlalchemy.exc.IntegrityError on the unique
        (trainer_user_id, player_profile_id) pair — the caller must check
        `get()` first under this codebase's established check-then-insert
        convention (see UserAdminService.create_user); this method does
        not catch the race itself."""
        record = TrainerPlayerAssociation(
            id=new_uuid(),
            trainer_user_id=trainer_user_id,
            player_profile_id=player_profile_id,
            share_link_id=share_link_id,
            status=AssociationStatus.ACTIVE.value,
            joined_at=utcnow(),
            updated_at=utcnow(),
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_active_for_player(
        self, player_profile_id: str
    ) -> list[tuple[TrainerPlayerAssociation, User, UserProfile]]:
        """Only Active associations whose trainer account is Active
        (FR-089) — every row this returns is switchable."""
        rows = await self._session.execute(
            select(TrainerPlayerAssociation, User, UserProfile)
            .join(User, User.id == TrainerPlayerAssociation.trainer_user_id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(
                TrainerPlayerAssociation.player_profile_id == player_profile_id,
                TrainerPlayerAssociation.status == AssociationStatus.ACTIVE.value,
                User.status == "active",
            )
        )
        return [(a, u, p) for a, u, p in rows.all()]

    async def list_active_for_account(
        self, account_user_id: str
    ) -> list[tuple[TrainerPlayerAssociation, PlayerProfile, User, UserProfile]]:
        """Every switchable pair across every live profile on one account
        (FR-118) — the parent's whole switcher, one query rather than one
        per profile."""
        rows = await self._session.execute(
            select(TrainerPlayerAssociation, PlayerProfile, User, UserProfile)
            .join(PlayerProfile, PlayerProfile.id == TrainerPlayerAssociation.player_profile_id)
            .join(User, User.id == TrainerPlayerAssociation.trainer_user_id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(
                PlayerProfile.account_user_id == account_user_id,
                PlayerProfile.removed_at.is_(None),
                TrainerPlayerAssociation.status == AssociationStatus.ACTIVE.value,
                User.status == "active",
            )
        )
        return [(a, pp, u, p) for a, pp, u, p in rows.all()]

    async def list_for_trainer(
        self,
        trainer_user_id: str,
        *,
        page: int,
        page_size: int,
        query: str | None,
    ) -> tuple[list[TrainerRosterRow], int]:
        # The responsible account is the player themselves for a SELF
        # profile and the parent for a CHILD one — both are
        # `player_profiles.account_user_id`, so one join reaches both
        # cases (FR-113, FR-116).
        base = (
            select(TrainerPlayerAssociation, PlayerProfile, User, UserProfile, ParentContact)
            .join(PlayerProfile, PlayerProfile.id == TrainerPlayerAssociation.player_profile_id)
            .join(User, User.id == PlayerProfile.account_user_id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .outerjoin(ParentContact, ParentContact.user_id == User.id)
            .where(
                TrainerPlayerAssociation.trainer_user_id == trainer_user_id,
                TrainerPlayerAssociation.status == AssociationStatus.ACTIVE.value,
            )
        )

        if query:
            pattern = f"%{query.lower()}%"
            base = base.where(
                or_(
                    func.lower(PlayerProfile.first_name).like(pattern),
                    func.lower(PlayerProfile.last_name).like(pattern),
                    func.lower(UserProfile.first_name).like(pattern),
                    func.lower(UserProfile.last_name).like(pattern),
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
            TrainerRosterRow(
                association=a,
                player_profile=pp,
                responsible_account=u,
                responsible_account_profile=p,
                responsible_parent_contact=c,
            )
            for a, pp, u, p, c in rows.all()
        ], total

    async def count_for_trainer(self, trainer_user_id: str) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                TrainerPlayerAssociation.trainer_user_id == trainer_user_id,
                TrainerPlayerAssociation.status == AssociationStatus.ACTIVE.value,
            )
        )
        return result.scalar_one()
