from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid, utcnow
from app.models.audit import ErasureRecord


class ErasureRepository:
    """Reachable through exactly one Super-Admin-only endpoint (FR-049);
    no method here joins this data into any ordinary account view."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        user_id: str,
        original_email: str,
        original_first_name: str,
        original_last_name: str,
        erased_by_user_id: str,
        reason: str,
    ) -> ErasureRecord:
        record = ErasureRecord(
            id=new_uuid(),
            user_id=user_id,
            original_email=original_email,
            original_first_name=original_first_name,
            original_last_name=original_last_name,
            erased_by_user_id=erased_by_user_id,
            reason=reason,
            erased_at=utcnow(),
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_for_user(self, user_id: str) -> ErasureRecord | None:
        result = await self._session.execute(
            select(ErasureRecord).where(ErasureRecord.user_id == user_id)
        )
        return result.scalar_one_or_none()
