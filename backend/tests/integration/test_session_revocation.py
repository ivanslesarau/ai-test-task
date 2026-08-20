from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_deactivation_immediately_revokes_every_open_session(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """FR-012, SC-007: an open session dies the moment its account leaves
    Active — not at its own natural expiry."""
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)

    trainer = await create_user(db_session, role=UserRole.TRAINER)
    trainer_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()

    app_client.cookies.set("pp_session", admin_token)
    deactivate = await app_client.post(f"/admin/users/{trainer.id}/deactivate", json={"version": 1})
    assert deactivate.status_code == 200

    app_client.cookies.set("pp_session", trainer_token)
    response = await app_client.get("/me/profile")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
