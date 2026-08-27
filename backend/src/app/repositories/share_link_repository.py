from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid, utcnow
from app.models.enums import ShareLinkKind
from app.models.share_link import ShareLink


class ShareLinkRepository:
    """Queries only — the five-part usability predicate (research.md R-21,
    data-model.md §16) belongs to ShareLinkService, not here."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_code(self, code: str) -> ShareLink | None:
        result = await self._session.execute(select(ShareLink).where(ShareLink.code == code))
        return result.scalar_one_or_none()

    async def get_current_for_trainer(self, trainer_user_id: str) -> ShareLink | None:
        result = await self._session.execute(
            select(ShareLink).where(
                ShareLink.trainer_user_id == trainer_user_id,
                ShareLink.kind == ShareLinkKind.PLAYER_STANDING.value,
                ShareLink.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def insert_standing_link(
        self, *, trainer_user_id: str, created_by_user_id: str, code: str
    ) -> ShareLink:
        link = ShareLink(
            id=new_uuid(),
            code=code,
            trainer_user_id=trainer_user_id,
            created_by_user_id=created_by_user_id,
            kind=ShareLinkKind.PLAYER_STANDING.value,
            target_email=None,
            expires_at=None,
            max_uses=None,
            use_count=0,
            is_active=True,
            revoked_at=None,
            created_at=utcnow(),
        )
        self._session.add(link)
        await self._session.flush()
        return link

    async def revoke(self, link: ShareLink) -> None:
        link.is_active = False
        link.revoked_at = utcnow()
        await self._session.flush()

    async def increment_use_count(self, link: ShareLink) -> None:
        link.use_count += 1
        await self._session.flush()

    @staticmethod
    def is_usable(link: ShareLink, *, now: datetime | None = None) -> bool:
        """The single five-part predicate (research.md R-21). Trainer
        Active-status is checked by the caller, which already has the
        trainer's User row loaded — duplicating that lookup here would
        cost a second query for every check."""
        now = now or utcnow()
        if not link.is_active or link.revoked_at is not None:
            return False
        if link.expires_at is not None and link.expires_at <= now:
            return False
        if link.max_uses is not None and link.use_count >= link.max_uses:
            return False
        return True
