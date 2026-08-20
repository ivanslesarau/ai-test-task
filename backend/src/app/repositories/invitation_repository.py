from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid, utcnow
from app.models.auth import CredentialSetupInvitation


class InvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: str, token_hash: str, issued_by_user_id: str, ttl_hours: int
    ) -> CredentialSetupInvitation:
        now = utcnow()
        record = CredentialSetupInvitation(
            id=new_uuid(),
            user_id=user_id,
            token_hash=token_hash,
            issued_by_user_id=issued_by_user_id,
            created_at=now,
            expires_at=now + timedelta(hours=ttl_hours),
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def find_by_token_hash(self, token_hash: str) -> CredentialSetupInvitation | None:
        result = await self._session.execute(
            select(CredentialSetupInvitation).where(
                CredentialSetupInvitation.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def supersede_outstanding_for_user(self, user_id: str) -> None:
        """Invalidates any earlier outstanding link for this account
        (FR-028) — called both when re-inviting and when a link is
        successfully consumed, so at most one is ever live."""
        result = await self._session.execute(
            select(CredentialSetupInvitation).where(
                CredentialSetupInvitation.user_id == user_id,
                CredentialSetupInvitation.consumed_at.is_(None),
                CredentialSetupInvitation.superseded_at.is_(None),
            )
        )
        now = utcnow()
        for record in result.scalars().all():
            record.superseded_at = now
        await self._session.flush()

    async def consume(self, record: CredentialSetupInvitation) -> None:
        record.consumed_at = utcnow()
        await self._session.flush()

    @staticmethod
    def is_usable(record: CredentialSetupInvitation) -> bool:
        return (
            record.consumed_at is None
            and record.superseded_at is None
            and record.expires_at > utcnow()
        )
