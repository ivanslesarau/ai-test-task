from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.enums import ImpersonationEndReason
from app.models.impersonation import ImpersonationSession


class ImpersonationRepository:
    """Append-only by construction, the same shape as `AuditRepository`
    (data-model.md §105, research.md R2-18): `insert` and `close` are the
    only writers, `close` is the one permitted update (closing an open
    row — the two SQLite triggers installed by revision 0011 are defence
    in depth for the identical rule, FR-055). No update or delete method
    beyond `close` is defined here.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        admin_user_id: str,
        target_user_id: str,
        auth_session_id: str | None,
        target_status_at_start: str,
        started_at: datetime,
        expires_at: datetime,
    ) -> ImpersonationSession:
        record = ImpersonationSession(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            auth_session_id=auth_session_id,
            target_status_at_start=target_status_at_start,
            started_at=started_at,
            expires_at=expires_at,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def close(
        self,
        record: ImpersonationSession,
        *,
        end_reason: ImpersonationEndReason,
        ended_at: datetime | None = None,
    ) -> None:
        record.ended_at = ended_at or utcnow()
        record.end_reason = end_reason.value
        await self._session.flush()

    async def get_by_id(self, impersonation_id: str) -> ImpersonationSession | None:
        result = await self._session.execute(
            select(ImpersonationSession).where(ImpersonationSession.id == impersonation_id)
        )
        return result.scalar_one_or_none()

    async def get_open_for_admin(self, admin_user_id: str) -> ImpersonationSession | None:
        """FR-048: at most one open impersonation per admin —
        `ix_impersonation_sessions_open` backs this query."""
        result = await self._session.execute(
            select(ImpersonationSession).where(
                ImpersonationSession.admin_user_id == admin_user_id,
                ImpersonationSession.ended_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_open_for_target(self, target_user_id: str) -> ImpersonationSession | None:
        """Whether this account is currently the *subject* of an open
        impersonation — the lifecycle hooks (`UserAdminService.deactivate`,
        `ErasureService.erase`) need this direction too (data-model.md
        §114); `ix_impersonation_sessions_target` backs it."""
        result = await self._session.execute(
            select(ImpersonationSession).where(
                ImpersonationSession.target_user_id == target_user_id,
                ImpersonationSession.ended_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def most_recent_ended_for_admin(self, admin_user_id: str) -> ImpersonationSession | None:
        """The row `ImpersonationService` derives `impersonation_ended`
        from (research.md R2-20) — reason and window filtering are the
        service's business rule, not this repository's."""
        result = await self._session.execute(
            select(ImpersonationSession)
            .where(
                ImpersonationSession.admin_user_id == admin_user_id,
                ImpersonationSession.ended_at.is_not(None),
            )
            .order_by(ImpersonationSession.ended_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        *,
        admin_user_id: str | None,
        target_user_id: str | None,
        started_from: datetime | None,
        started_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ImpersonationSession], int]:
        """FR-053, FR-054: US7's history read. Built now (costs nothing
        extra) since the repository is already here for US6's own writes;
        the router that calls it is US7's, not this phase's."""
        query = select(ImpersonationSession)
        if admin_user_id is not None:
            query = query.where(ImpersonationSession.admin_user_id == admin_user_id)
        if target_user_id is not None:
            query = query.where(ImpersonationSession.target_user_id == target_user_id)
        if started_from is not None:
            query = query.where(ImpersonationSession.started_at >= started_from)
        if started_to is not None:
            query = query.where(ImpersonationSession.started_at <= started_to)

        total = (
            await self._session.execute(select(func.count()).select_from(query.subquery()))
        ).scalar_one()

        rows = (
            (
                await self._session.execute(
                    query.order_by(ImpersonationSession.started_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total
