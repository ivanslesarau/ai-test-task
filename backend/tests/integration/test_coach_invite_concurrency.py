"""US2 (tasks.md T544): FR-018's concurrency guard, and the shared 404
body every unusable invitation returns."""

import asyncio
from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.errors import InvitationLinkInvalid
from app.db.base import utcnow
from app.db.engine import _set_sqlite_pragmas
from app.models.coach_invitation import CoachInvitation
from app.models.role_details import CoachDetail
from app.services.coach_invitation_service import CoachInvitationService
from app.services.ports.email_sender import get_email_sender
from tests.helpers import create_coach, create_coach_invitation, create_trainer_with_link


async def test_two_simultaneous_acceptances_leave_exactly_one_winner(
    db_session: AsyncSession,
) -> None:
    """Two coach accounts racing to accept the same invitation — only one
    may win the `awaiting -> accepted` transition (FR-018); the other
    sees the same 404 any other dead link returns."""
    trainer, _ = await create_trainer_with_link(db_session, business_name="Race Academy")
    invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="racer@example.org"
    )
    coach = await create_coach(db_session, email="racer@example.org")
    await db_session.commit()
    # Captured before the race: after it, this test's own `db_session`'s
    # identity-mapped objects are stale (the two racing calls commit
    # through their own engines/sessions), and even a bare attribute
    # read like `coach.id` would trigger a synchronous refresh outside
    # any async context once those objects are expired. Every check below
    # goes through a fresh `execute()` keyed on these plain strings.
    coach_id, trainer_id, invitation_id = coach.id, trainer.id, invitation.id

    settings = get_settings()
    database_url = settings.database_url

    async def _accept() -> Exception | None:
        engine = create_async_engine(database_url)
        event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
        sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessionmaker() as session:
                service = CoachInvitationService(session, settings, get_email_sender(settings))
                fresh_coach = await session.get(type(coach), coach_id)
                assert fresh_coach is not None
                await service.accept(raw_token, current_user=fresh_coach)
                await session.commit()
                return None
        except InvitationLinkInvalid as exc:
            return exc
        finally:
            await engine.dispose()

    results = await asyncio.gather(_accept(), _accept())
    successes = [r for r in results if r is None]
    failures = [r for r in results if r is not None]
    assert len(successes) == 1
    assert len(failures) == 1

    db_session.expire_all()

    detail = (
        await db_session.execute(select(CoachDetail).where(CoachDetail.user_id == coach_id))
    ).scalar_one()
    assert detail.trainer_user_id == trainer_id

    row = (
        await db_session.execute(select(CoachInvitation).where(CoachInvitation.id == invitation_id))
    ).scalar_one()
    assert row.state == "accepted"

    accepted_count = (
        await db_session.execute(
            select(func.count()).select_from(
                select(CoachInvitation)
                .where(
                    CoachInvitation.id == invitation_id,
                    CoachInvitation.state == "accepted",
                )
                .subquery()
            )
        )
    ).scalar_one()
    assert accepted_count == 1


async def test_spent_revoked_superseded_expired_and_inactive_trainer_are_all_the_same_404(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.enums import AccountStatus, CoachInvitationState

    trainer, _ = await create_trainer_with_link(db_session)
    inactive_trainer, _ = await create_trainer_with_link(db_session, status=AccountStatus.INACTIVE)

    spent, spent_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="spent@example.org"
    )
    accepted_coach = await create_coach(db_session, email="spent-coach@example.org")
    # All three set together before the next flush — `ck_coach_invitations_
    # terminal_pair` requires `accepted_at` whenever `state = 'accepted'`.
    spent.state = CoachInvitationState.ACCEPTED.value
    spent.accepted_by_user_id = accepted_coach.id
    spent.accepted_at = utcnow()

    revoked, revoked_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="revoked@example.org"
    )
    revoked.state = CoachInvitationState.REVOKED.value
    revoked.revoked_at = utcnow()

    superseded, superseded_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="superseded@example.org"
    )
    superseded.state = CoachInvitationState.SUPERSEDED.value
    superseded.superseded_at = utcnow()

    expired, expired_token = await create_coach_invitation(
        db_session,
        trainer=trainer,
        invited_email="expired@example.org",
        expires_at=utcnow() - timedelta(days=1),
    )

    inactive, inactive_token = await create_coach_invitation(
        db_session, trainer=inactive_trainer, invited_email="orphaned@example.org"
    )
    await db_session.commit()

    for token in (spent_token, revoked_token, superseded_token, expired_token, inactive_token):
        response = await app_client.get(f"/coach-invitations/{token}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "invitation_link_invalid"

    unknown_response = await app_client.get(
        "/coach-invitations/clearly-not-a-real-token-value-0000"
    )
    assert unknown_response.status_code == 404
    assert unknown_response.json()["error"]["code"] == "invitation_link_invalid"
