"""US6 (tasks.md T619, FR-052, SC-015, research.md R2-16): a change made
while impersonating writes one audit entry naming the target as
`actor_user_id` and the admin as `impersonator_user_id`; an ordinary
change leaves the column `NULL`.
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEntry
from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_an_action_while_impersonating_names_both_parties(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    app_client.cookies.set("pp_session", admin_token)
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    issued = await app_client.post(
        "/trainer/coach-invitations", json={"email": "prospect@example.org"}
    )
    assert issued.status_code == 201

    result = await db_session.execute(
        select(AuditEntry).where(AuditEntry.action == "coach_invitation_issued")
    )
    entry = result.scalars().first()
    assert entry is not None
    assert entry.actor_user_id == trainer.id
    assert entry.impersonator_user_id == admin.id


async def test_an_ordinary_action_leaves_the_impersonator_column_null(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    trainer_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()

    app_client.cookies.set("pp_session", trainer_token)
    issued = await app_client.post(
        "/trainer/coach-invitations", json={"email": "prospect@example.org"}
    )
    assert issued.status_code == 201

    result = await db_session.execute(
        select(AuditEntry).where(AuditEntry.action == "coach_invitation_issued")
    )
    entry = result.scalars().first()
    assert entry is not None
    assert entry.actor_user_id == trainer.id
    assert entry.impersonator_user_id is None
