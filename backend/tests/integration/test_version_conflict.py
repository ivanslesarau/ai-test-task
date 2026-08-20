from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_stale_version_is_refused_and_changes_nothing(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/admin/users/{trainer.id}/deactivate", json={"version": 999})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stale_version"

    unchanged = await app_client.get(f"/admin/users/{trainer.id}")
    assert unchanged.json()["status"] == "active"
    assert unchanged.json()["version"] == 1
