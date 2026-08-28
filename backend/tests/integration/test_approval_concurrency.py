"""quickstart.md scenario 12.14 (US12, tasks.md T400, SC-038). Two
approvals of one request racing each other must produce exactly one
success and one `request_already_resolved`, and exactly one association
— proven by racing two independent connections, since no single-session
walk can exercise this (research.md R-41, mirroring the shape
test_family_profiles.py's 9.11 uses for the one-self-profile race)."""

import asyncio
from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.errors import RequestAlreadyResolved
from app.db.base import utcnow
from app.db.engine import _set_sqlite_pragmas
from app.models.approval import ApprovalRequest
from app.models.association import TrainerPlayerAssociation
from app.services.approval_service import ApprovalService
from app.services.ports.email_sender import get_email_sender
from tests.helpers import create_family, create_session_cookie, create_trainer_with_link


async def test_racing_approvals_of_one_request_yield_exactly_one_success(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    trainer, link = await create_trainer_with_link(db_session, business_name="Race Academy")
    await db_session.commit()

    child_token = await create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", child_token)
    blocked = await app_client.post(f"/join/{link.code}/accept")
    await db_session.commit()
    assert blocked.status_code == 403

    request = (
        await db_session.execute(
            select(ApprovalRequest).where(ApprovalRequest.trainer_user_id == trainer.id)
        )
    ).scalar_one()
    request_id = request.id

    settings = get_settings()
    database_url = settings.database_url

    async def _approve() -> Exception | None:
        engine = create_async_engine(database_url)
        event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
        sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessionmaker() as session:
                service = ApprovalService(session, settings, get_email_sender(settings))
                await service.approve(parent.id, request_id, note=None)
                await session.commit()
                return None
        except RequestAlreadyResolved as exc:
            return exc
        finally:
            await engine.dispose()

    results = await asyncio.gather(_approve(), _approve())
    successes = [r for r in results if r is None]
    failures = [r for r in results if r is not None]
    assert len(successes) == 1
    assert len(failures) == 1

    association_count = (
        await db_session.execute(
            select(func.count()).select_from(
                select(TrainerPlayerAssociation)
                .where(
                    TrainerPlayerAssociation.trainer_user_id == trainer.id,
                    TrainerPlayerAssociation.player_profile_id == profiles[0].id,
                )
                .subquery()
            )
        )
    ).scalar_one()
    assert association_count == 1


async def test_an_approval_racing_the_expiry_deadline_either_fully_succeeds_or_not_at_all(
    db_session: AsyncSession,
) -> None:
    """The second half of SC-038: an approval arriving right at the
    deadline must not leave a half-applied state — either the
    conditional UPDATE takes it (still live, `expires_at > now`) and the
    executor runs, or it does not and nothing changes (research.md R-41,
    R-42)."""
    from tests.helpers import create_approval_request

    parent, profiles, _ = await create_family(db_session, children=1)
    trainer, link = await create_trainer_with_link(db_session, business_name="Deadline Academy")
    await db_session.commit()

    settings = get_settings()

    # A request one second from expiring — the approval below must land
    # before it, so this proves "approval before the deadline still
    # fully applies", the complement of test_approval_expiry.py's
    # "after the deadline, unapprovable".
    request = await create_approval_request(
        db_session,
        player_profile_id=profiles[0].id,
        parent_user_id=parent.id,
        trainer_user_id=trainer.id,
        share_link_id=link.id,
        expires_at=utcnow() + timedelta(seconds=5),
    )
    await db_session.commit()

    service = ApprovalService(db_session, settings, get_email_sender(settings))
    resolved = await service.approve(parent.id, request.id, note=None)
    await db_session.commit()

    assert resolved.status == "approved"
    association = (
        await db_session.execute(
            select(TrainerPlayerAssociation).where(
                TrainerPlayerAssociation.trainer_user_id == trainer.id,
                TrainerPlayerAssociation.player_profile_id == profiles[0].id,
            )
        )
    ).scalar_one()
    assert association.status == "active"
