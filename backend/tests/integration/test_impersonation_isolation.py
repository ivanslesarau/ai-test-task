"""US6 (tasks.md T618, FR-049): impersonation touches no session but the
admin's own. The impersonated person's sessions are neither revoked nor
have their sliding expiry advanced by the admin's activity.
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import Session as SessionModel
from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_the_targets_own_session_is_untouched_by_the_impersonation(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    trainer_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()

    result = await db_session.execute(
        select(SessionModel).where(SessionModel.user_id == trainer.id)
    )
    trainer_session = result.scalar_one()
    trainer_last_seen_before = trainer_session.last_seen_at
    trainer_expires_before = trainer_session.expires_at
    assert trainer_session.revoked_at is None

    app_client.cookies.set("pp_session", admin_token)
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    # Several requests as the impersonating admin, riding the target's
    # identity — none of them may touch the target's OWN session row.
    for _ in range(3):
        response = await app_client.get("/auth/session")
        assert response.status_code == 200

    await db_session.refresh(trainer_session)
    assert trainer_session.revoked_at is None
    assert trainer_session.last_seen_at == trainer_last_seen_before
    assert trainer_session.expires_at == trainer_expires_before

    # The target's own cookie still works normally and is unaffected.
    app_client.cookies.set("pp_session", trainer_token)
    own_view = await app_client.get("/auth/session")
    assert own_view.status_code == 200
    body = own_view.json()
    assert body["id"] == trainer.id
    assert body["impersonation"] is None
