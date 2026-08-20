from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_former_email_is_reusable_after_erasure(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    coach = await create_user(db_session, role=UserRole.COACH, email="reusable@example.org")
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    await app_client.post(f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "x"})

    response = await app_client.post(
        "/admin/users",
        json={
            "role": "coach",
            "email": "reusable@example.org",
            "first_name": "New",
            "last_name": "Person",
            "phone": "+14155552671",
        },
    )

    assert response.status_code == 201


async def test_creating_an_account_with_the_placeholder_pattern_is_rejected(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(
        "/admin/users",
        json={
            "role": "coach",
            "email": "deleted_11111111-1111-1111-1111-111111111111@example.com",
            "first_name": "X",
            "last_name": "Y",
            "phone": "+14155552671",
        },
    )

    assert response.status_code == 422
