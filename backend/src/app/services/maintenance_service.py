from datetime import timedelta
from typing import cast

from sqlalchemy import CursorResult, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.association import LinkLookupAttempt
from app.models.auth import Session as SessionModel
from app.models.auth import SignInAttempt

# Retained briefly past expiry/revocation so a request arriving on a
# just-revoked session is distinguishable from one on a token that never
# existed (data-model.md §5) — this is how long "briefly" is.
_SESSION_RETENTION = timedelta(days=1)
_SIGN_IN_ATTEMPT_RETENTION = timedelta(days=30)
# Same retention as sign_in_attempts — both back a sliding-window
# throttle over the same 15-minute window (research.md R-30).
_LINK_LOOKUP_ATTEMPT_RETENTION = timedelta(days=30)


class MaintenanceService:
    """Prunes rows whose only purpose was a time-bounded check that has
    already passed — sessions and rate-limit attempt records. Neither
    table is a historical record the platform reports on, unlike
    audit_entries and erasure_records, which this service never touches.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self._session = db_session

    async def prune_expired_sessions(self) -> int:
        cutoff = utcnow() - _SESSION_RETENTION
        result = cast(
            CursorResult,
            await self._session.execute(
                delete(SessionModel).where(
                    (SessionModel.expires_at < cutoff) | (SessionModel.revoked_at < cutoff)
                )
            ),
        )
        return result.rowcount

    async def prune_old_sign_in_attempts(self) -> int:
        cutoff = utcnow() - _SIGN_IN_ATTEMPT_RETENTION
        result = cast(
            CursorResult,
            await self._session.execute(
                delete(SignInAttempt).where(SignInAttempt.attempted_at < cutoff)
            ),
        )
        return result.rowcount

    async def prune_old_link_lookup_attempts(self) -> int:
        cutoff = utcnow() - _LINK_LOOKUP_ATTEMPT_RETENTION
        result = cast(
            CursorResult,
            await self._session.execute(
                delete(LinkLookupAttempt).where(LinkLookupAttempt.attempted_at < cutoff)
            ),
        )
        return result.rowcount
