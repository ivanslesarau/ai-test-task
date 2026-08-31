"""US6 (tasks.md T617, FR-045, FR-046, SC-014, research.md R2-15): exit
succeeds while the effective user is a Trainer — the asymmetric route —
and a session past its deadline resolves to the admin with
`impersonation_ended.end_reason = timed_out`. No impersonation exceeds
the one-hour ceiling.
"""

from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.enums import UserRole
from app.models.impersonation import ImpersonationSession
from tests.helpers import create_session_cookie, create_user


async def _start(app_client: AsyncClient, db_session: AsyncSession) -> tuple[str, str]:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201
    return admin.id, trainer.id


async def test_exit_succeeds_while_the_effective_user_is_a_trainer(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """R2-15's asymmetric route: a Super-Admin-role gate here would lock
    the admin inside the impersonation, since the effective user during
    it is a Trainer, not a Super Admin."""
    admin_id, _trainer_id = await _start(app_client, db_session)

    exited = await app_client.delete("/admin/impersonations/current")
    assert exited.status_code == 204

    session = await app_client.get("/auth/session")
    assert session.status_code == 200
    body = session.json()
    assert body["id"] == admin_id
    assert body["impersonation"] is None


async def test_exit_with_no_open_impersonation_is_404(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.delete("/admin/impersonations/current")

    assert response.status_code == 404


async def test_a_session_past_its_deadline_resolves_to_the_admin_as_timed_out(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin_id, _trainer_id = await _start(app_client, db_session)

    result = await db_session.execute(
        select(ImpersonationSession).where(ImpersonationSession.admin_user_id == admin_id)
    )
    record = result.scalar_one()
    record.expires_at = utcnow() - timedelta(seconds=1)
    await db_session.commit()

    session = await app_client.get("/auth/session")
    assert session.status_code == 200
    body = session.json()
    assert body["id"] == admin_id
    assert body["impersonation"] is None
    assert body["impersonation_ended"] is not None
    assert body["impersonation_ended"]["end_reason"] == "timed_out"


async def test_no_impersonation_exceeds_the_one_hour_ceiling(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin_id, _trainer_id = await _start(app_client, db_session)

    result = await db_session.execute(
        select(ImpersonationSession).where(ImpersonationSession.admin_user_id == admin_id)
    )
    record = result.scalar_one()
    assert (record.expires_at - record.started_at) <= timedelta(hours=1)
