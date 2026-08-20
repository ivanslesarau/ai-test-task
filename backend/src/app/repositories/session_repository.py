from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.auth import Session as SessionModel


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, user_id: str, token_hash: str, idle_days: int) -> SessionModel:
        now = utcnow()
        record = SessionModel(
            user_id=user_id,
            token_hash=token_hash,
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=idle_days),
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def find_active_by_token_hash(self, token_hash: str) -> SessionModel | None:
        result = await self._session.execute(
            select(SessionModel).where(
                SessionModel.token_hash == token_hash,
                SessionModel.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def touch(self, record: SessionModel, *, idle_days: int) -> None:
        """Advance last-seen and expiry, implementing the sliding
        inactivity window (FR-011)."""
        now = utcnow()
        record.last_seen_at = now
        record.expires_at = now + timedelta(days=idle_days)
        await self._session.flush()

    async def revoke(self, record: SessionModel) -> None:
        record.revoked_at = utcnow()
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: str) -> None:
        """Revoked in the same transaction as a status change, so access
        dies immediately rather than at natural session expiry
        (FR-012, SC-007)."""
        result = await self._session.execute(
            select(SessionModel).where(
                SessionModel.user_id == user_id,
                SessionModel.revoked_at.is_(None),
            )
        )
        now = utcnow()
        for record in result.scalars().all():
            record.revoked_at = now
        await self._session.flush()

    @staticmethod
    def is_usable(record: SessionModel, *, now: datetime | None = None) -> bool:
        now = now or utcnow()
        return record.revoked_at is None and record.expires_at > now
