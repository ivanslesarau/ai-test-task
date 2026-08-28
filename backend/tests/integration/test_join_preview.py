from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.enums import AccountStatus, UserRole
from tests.helpers import (
    create_association,
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def test_valid_code_returns_only_business_name_branding_and_viewer_state(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, link = await create_trainer_with_link(db_session, business_name="Acme Academy")
    await db_session.commit()

    response = await app_client.get(f"/join/{link.code}")

    assert response.status_code == 200
    body = response.json()
    assert body["trainer_display_name"] == "Acme Academy"
    assert body["viewer"]["state"] == "anonymous"
    assert set(body.keys()) == {"trainer_display_name", "branding", "viewer"}
    assert trainer.id not in str(body)


async def test_unknown_code_and_revoked_code_produce_identical_404_bodies(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    link.is_active = False
    await db_session.commit()

    unknown_response = await app_client.get("/join/definitely-not-a-real-code")
    revoked_response = await app_client.get(f"/join/{link.code}")

    assert unknown_response.status_code == 404
    assert revoked_response.status_code == 404
    assert unknown_response.json() == revoked_response.json()
    assert unknown_response.json()["error"]["code"] == "invitation_link_invalid"


async def test_expired_link_is_refused(app_client: AsyncClient, db_session: AsyncSession) -> None:
    _, link = await create_trainer_with_link(db_session)
    link.expires_at = utcnow() - timedelta(seconds=1)
    await db_session.commit()

    response = await app_client.get(f"/join/{link.code}")
    assert response.status_code == 404


async def test_link_for_a_deactivated_trainer_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, link = await create_trainer_with_link(db_session)
    trainer.status = AccountStatus.INACTIVE.value
    await db_session.commit()

    response = await app_client.get(f"/join/{link.code}")
    assert response.status_code == 404


async def test_signed_in_player_already_associated_sees_that_state(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, link = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get(f"/join/{link.code}")

    assert response.status_code == 200
    assert response.json()["viewer"]["state"] == "already_associated"


async def test_signed_in_player_not_yet_associated_can_join(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get(f"/join/{link.code}")

    assert response.status_code == 200
    assert response.json()["viewer"]["state"] == "can_join"


async def test_signed_in_coach_cannot_join(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    coach = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get(f"/join/{link.code}")

    assert response.status_code == 200
    assert response.json()["viewer"]["state"] == "role_cannot_join"
