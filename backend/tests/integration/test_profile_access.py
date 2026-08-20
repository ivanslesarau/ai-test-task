from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_a_signed_in_user_only_sees_their_own_profile(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    coach = await create_user(db_session, role=UserRole.COACH, first_name="Cody")
    trainer = await create_user(db_session, role=UserRole.TRAINER, first_name="Tara")
    coach_token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", coach_token)

    response = await app_client.get("/me/profile")

    assert response.status_code == 200
    assert response.json()["first_name"] == "Cody"
    assert response.json()["id"] != trainer.id


async def test_there_is_no_route_to_read_another_users_profile_directly(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """/me/profile has no id parameter — it always resolves to the caller.
    A Super Admin reads another account through /admin/users/{id}
    (US2/US4/US5), a separate endpoint with its own role gate; there is no
    way to address another person's profile through /me/profile at all."""
    coach = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/me/profile")
    assert response.json()["id"] == coach.id
