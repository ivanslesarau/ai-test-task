from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.auth import SignInAttempt


class SignInAttemptRepository:
    """Durable failed-attempt records backing the rate limit (R-06).

    Persisted rather than held in process memory so a restart cannot clear
    an attacker's counter (research.md R-06).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, *, email: str, client_ip: str, successful: bool) -> None:
        self._session.add(
            SignInAttempt(
                email=email.lower(),
                client_ip=client_ip,
                attempted_at=utcnow(),
                successful=successful,
            )
        )
        await self._session.flush()

    async def count_recent_failures(
        self, *, email: str, client_ip: str, window_minutes: int
    ) -> int:
        """The larger of the failure count keyed by email and by client
        address — either dimension exceeding the limit refuses the
        attempt, so credential stuffing against one account and spraying
        from one source are both caught."""
        since = utcnow() - timedelta(minutes=window_minutes)

        by_email = (
            await self._session.execute(
                select(func.count()).where(
                    SignInAttempt.email == email.lower(),
                    SignInAttempt.successful.is_(False),
                    SignInAttempt.attempted_at >= since,
                )
            )
        ).scalar_one()

        by_ip = (
            await self._session.execute(
                select(func.count()).where(
                    SignInAttempt.client_ip == client_ip,
                    SignInAttempt.successful.is_(False),
                    SignInAttempt.attempted_at >= since,
                )
            )
        ).scalar_one()

        return max(by_email, by_ip)
