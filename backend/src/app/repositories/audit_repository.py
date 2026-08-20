from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.audit import AuditEntry


class AuditRepository:
    """Append-only by construction: only `add` and `list_for_target` exist.

    No update or delete method is defined here — FR-055 requires that no
    one can alter or remove an audit entry through the platform, and the
    Alembic revision 0004 triggers are defence in depth for the same rule.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        action: str,
        actor_user_id: str | None,
        target_user_id: str | None,
        reason: str | None = None,
        detail: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            action=action,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            reason=reason,
            detail=detail,
            occurred_at=utcnow(),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_for_target(
        self, target_user_id: str, *, page: int, page_size: int
    ) -> tuple[list[AuditEntry], int]:
        base = select(AuditEntry).where(AuditEntry.target_user_id == target_user_id)

        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()

        rows = (
            (
                await self._session.execute(
                    base.order_by(AuditEntry.occurred_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )

        return list(rows), total
