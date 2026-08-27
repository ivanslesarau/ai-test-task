from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.models.enums import AccountStatus, AssociationStatus
from app.models.role_details import TrainerOrganization
from app.models.user import User
from app.repositories.association_repository import AssociationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.branding import build_portal_branding_out
from app.schemas.trainer_context import TrainerContextEntry, TrainerContextList


class TrainerContextService:
    """Resolve-and-repair the active trainer context (research.md R-24),
    list it for the switcher, and switch it. The only place
    `active_trainer_user_id` is trusted as read — every other caller goes
    through this service rather than reading the column directly."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._users = UserRepository(db_session)
        self._associations = AssociationRepository(db_session)

    async def resolve_active_trainer_id(self, player: User) -> str | None:
        """A stored context whose association is missing, inactive, or
        whose trainer is not Active is replaced and the correction
        written back (FR-089). Returns None only when the player holds no
        Active association at all — a valid state, not an error."""
        player_detail = await self._users.get_role_detail(player)
        if not isinstance(player_detail, tuple) or player_detail[0] is None:
            return None
        detail = player_detail[0]

        active_rows = await self._associations.list_active_for_player(player.id)
        if not active_rows:
            if detail.active_trainer_user_id is not None:
                detail.active_trainer_user_id = None
            return None

        valid_trainer_ids = {trainer_user.id for _, trainer_user, _ in active_rows}
        if detail.active_trainer_user_id not in valid_trainer_ids:
            detail.active_trainer_user_id = active_rows[0][1].id
        return detail.active_trainer_user_id

    async def list_for_player(self, player: User) -> TrainerContextList:
        active_trainer_id = await self.resolve_active_trainer_id(player)
        rows = await self._associations.list_active_for_player(player.id)

        entries = []
        for association, trainer_user, _trainer_profile in rows:
            trainer_org = await self._users.get_role_detail(trainer_user)
            business_name = (
                trainer_org.business_name if isinstance(trainer_org, TrainerOrganization) else ""
            )
            entries.append(
                TrainerContextEntry(
                    trainer_id=trainer_user.id,
                    display_name=business_name,
                    branding=build_portal_branding_out(trainer_org),
                    joined_at=association.joined_at,
                )
            )

        return TrainerContextList(active_trainer_id=active_trainer_id, trainers=entries)

    async def switch(self, player: User, trainer_id: str) -> TrainerContextList:
        """404, never 403, for a trainer the caller holds no Active
        association with — a role-style refusal would confirm that
        trainer exists (FR-090)."""
        association = await self._associations.get(
            trainer_user_id=trainer_id, player_user_id=player.id
        )
        if association is None or association.status != AssociationStatus.ACTIVE.value:
            raise NotFound("No such trainer.")

        trainer = await self._users.get_by_id(trainer_id)
        if trainer is None or trainer.status_enum is not AccountStatus.ACTIVE:
            raise NotFound("No such trainer.")

        player_detail = await self._users.get_role_detail(player)
        if isinstance(player_detail, tuple) and player_detail[0] is not None:
            player_detail[0].active_trainer_user_id = trainer_id

        return await self.list_for_player(player)
