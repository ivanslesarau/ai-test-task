from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_trainer_with_link, create_user


async def _sign_in_trainer(app_client: AsyncClient, db_session: AsyncSession):
    trainer, link = await create_trainer_with_link(db_session)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return trainer


async def test_read_default_branding(app_client: AsyncClient, db_session: AsyncSession) -> None:
    await _sign_in_trainer(app_client, db_session)

    response = await app_client.get("/me/branding")

    assert response.status_code == 200
    body = response.json()
    assert body["logo_url"] is None
    assert body["primary_color"] is None


async def test_set_a_colour(app_client: AsyncClient, db_session: AsyncSession) -> None:
    await _sign_in_trainer(app_client, db_session)

    response = await app_client.patch("/me/branding", json={"primary_color": "#3366CC"})

    assert response.status_code == 200
    assert response.json()["primary_color"] == "#3366cc"


async def test_omitted_key_leaves_colour_unchanged(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(app_client, db_session)
    await app_client.patch("/me/branding", json={"primary_color": "#3366cc"})

    # Empty body: the key is omitted entirely, not sent as null.
    response = await app_client.patch("/me/branding", json={})

    assert response.status_code == 200
    assert response.json()["primary_color"] == "#3366cc"


async def test_explicit_null_clears_the_colour(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(app_client, db_session)
    await app_client.patch("/me/branding", json={"primary_color": "#3366cc"})

    response = await app_client.patch("/me/branding", json={"primary_color": None})

    assert response.status_code == 200
    assert response.json()["primary_color"] is None


async def test_reset_clears_both_logo_and_colour(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(app_client, db_session)
    await app_client.patch("/me/branding", json={"primary_color": "#3366cc"})

    response = await app_client.post("/me/branding/reset")

    assert response.status_code == 200
    body = response.json()
    assert body["logo_url"] is None
    assert body["primary_color"] is None


async def test_malformed_colour_is_rejected(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(app_client, db_session)

    response = await app_client.patch("/me/branding", json={"primary_color": "blue"})

    assert response.status_code == 422


async def test_coach_and_player_are_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    coach = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    read_response = await app_client.get("/me/branding")
    write_response = await app_client.patch("/me/branding", json={"primary_color": "#3366cc"})

    assert read_response.status_code == 403
    assert write_response.status_code == 403
