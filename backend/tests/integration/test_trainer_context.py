from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import (
    create_association,
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def test_switching_context_changes_active_ids(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    trainer_b, _ = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer_a.id, player_profile_id=profile.id)
    await create_association(db_session, trainer_id=trainer_b.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.put(
        "/me/context", json={"player_profile_id": profile.id, "trainer_id": trainer_b.id}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["active_trainer_id"] == trainer_b.id
    assert body["active_player_profile_id"] == profile.id
    assert {c["trainer_id"] for c in body["contexts"]} == {trainer_a.id, trainer_b.id}


async def test_session_restores_last_used_context(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    trainer_b, _ = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer_a.id, player_profile_id=profile.id)
    await create_association(db_session, trainer_id=trainer_b.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    await app_client.put(
        "/me/context", json={"player_profile_id": profile.id, "trainer_id": trainer_b.id}
    )

    session_response = await app_client.get("/auth/session")
    assert session_response.status_code == 200
    body = session_response.json()
    assert body["active_trainer_id"] == trainer_b.id
    assert body["active_player_profile_id"] == profile.id
    assert body["context_count"] == 2


async def test_switching_to_an_unassociated_trainer_returns_404_not_403(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    other_trainer, _ = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer_a.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.put(
        "/me/context", json={"player_profile_id": profile.id, "trainer_id": other_trainer.id}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] != "forbidden"


async def test_switching_to_a_profile_not_on_the_account_returns_404(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """R-48: a profile that exists but is not reachable by this caller
    (here, on a different account entirely) is a 404, exactly like an
    unassociated trainer — never confirmed to exist."""
    trainer, _ = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)

    other_player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    other_profile = await create_player_profile(db_session, account=other_player, kind="self")

    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.put(
        "/me/context", json={"player_profile_id": other_profile.id, "trainer_id": trainer.id}
    )

    assert response.status_code == 404


async def test_a_player_with_one_trainer_has_no_switcher_signal(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/me/contexts")

    assert response.status_code == 200
    body = response.json()
    assert len(body["contexts"]) == 1
    assert body["active_trainer_id"] == trainer.id
    assert body["active_player_profile_id"] == profile.id


async def test_non_player_role_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    coach = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/me/contexts")
    assert response.status_code == 403
