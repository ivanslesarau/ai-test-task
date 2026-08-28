from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.player_profile import ActiveTrainingContext


class ActiveTrainingContextRepository:
    """Queries only, over the one-row-per-viewer table `research.md R-36`
    describes. `TrainingContextService` is the only caller — the stored
    pair is never trusted as read anywhere else (data-model.md §27)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_user(self, user_id: str) -> ActiveTrainingContext | None:
        return await self._session.get(ActiveTrainingContext, user_id)

    async def delete_for_user(self, user_id: str) -> None:
        """Erasure (data-model.md §30): an erased account has no context
        to be in, for itself or for any child sign-in it granted."""
        record = await self.get_for_user(user_id)
        if record is not None:
            await self._session.delete(record)
            await self._session.flush()

    async def upsert(
        self, *, user_id: str, player_profile_id: str | None, trainer_user_id: str | None
    ) -> ActiveTrainingContext:
        """Both columns are written together — a row with one set and the
        other `NULL` is never written, matching data-model.md §27's rule
        that such a row is not a state this service produces."""
        record = await self.get_for_user(user_id)
        if record is None:
            record = ActiveTrainingContext(
                user_id=user_id,
                player_profile_id=player_profile_id,
                trainer_user_id=trainer_user_id,
                updated_at=utcnow(),
            )
            self._session.add(record)
        else:
            record.player_profile_id = player_profile_id
            record.trainer_user_id = trainer_user_id
            record.updated_at = utcnow()
        await self._session.flush()
        return record
