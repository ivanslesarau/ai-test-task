"""tasks.md T401 (FR-139, research.md R-40). Racing two creations of the
same child-and-trainer request must leave exactly one live row — the
partial unique index `uq_approval_requests_live`, not a service-level
check that a second concurrent caller could slip past."""

import asyncio

from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.engine import _set_sqlite_pragmas
from app.models.approval import ApprovalRequest
from app.models.enums import ApprovalRequestKind
from app.repositories.approval_repository import ApprovalRepository
from tests.helpers import create_family, create_trainer_with_link


async def test_racing_two_creations_of_the_same_request_leaves_exactly_one(
    db_session: AsyncSession,
) -> None:
    parent, profiles, _ = await create_family(db_session, children=1)
    trainer, _ = await create_trainer_with_link(db_session, business_name="Duplicate Academy")
    await db_session.commit()

    player_profile_id = profiles[0].id
    trainer_id = trainer.id
    parent_id = parent.id
    database_url = get_settings().database_url

    async def _insert() -> Exception | None:
        engine = create_async_engine(database_url)
        event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
        sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessionmaker() as session:
                repo = ApprovalRepository(session)
                await repo.insert(
                    player_profile_id=player_profile_id,
                    parent_user_id=parent_id,
                    kind=ApprovalRequestKind.JOIN_TRAINER.value,
                    trainer_user_id=trainer_id,
                )
                await session.commit()
                return None
        except Exception as exc:  # noqa: BLE001 — the race's outcome is the point
            return exc
        finally:
            await engine.dispose()

    results = await asyncio.gather(_insert(), _insert())
    successes = [r for r in results if r is None]
    failures = [r for r in results if r is not None]
    assert len(successes) == 1
    assert len(failures) == 1

    live_count = (
        await db_session.execute(
            select(func.count()).select_from(
                select(ApprovalRequest)
                .where(
                    ApprovalRequest.player_profile_id == player_profile_id,
                    ApprovalRequest.trainer_user_id == trainer_id,
                    ApprovalRequest.status == "pending_parent_approval",
                )
                .subquery()
            )
        )
    ).scalar_one()
    assert live_count == 1
