from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.association import LinkLookupAttempt


class LinkLookupAttemptRepository:
    """Durable counter behind the join-link throttle (research.md R-30),
    shaped like SignInAttemptRepository but keyed by client_ip alone — an
    invalid invitation code identifies no account, so there is no second
    dimension to count."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, *, client_ip: str, successful: bool) -> None:
        self._session.add(
            LinkLookupAttempt(
                client_ip=client_ip,
                attempted_at=utcnow(),
                successful=successful,
            )
        )
        await self._session.flush()

    async def count_recent_failures(self, *, client_ip: str, window_minutes: int) -> int:
        since = utcnow() - timedelta(minutes=window_minutes)
        result = await self._session.execute(
            select(func.count()).where(
                LinkLookupAttempt.client_ip == client_ip,
                LinkLookupAttempt.successful.is_(False),
                LinkLookupAttempt.attempted_at >= since,
            )
        )
        return result.scalar_one()
