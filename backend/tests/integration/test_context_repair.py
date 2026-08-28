"""FR-089, FR-120: a stored active context whose trainer becomes
unavailable is repaired on read — the player is moved to another Active
association, or, if none remains, told plainly they belong to no trainer.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus, UserRole
from tests.helpers import (
    create_association,
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def test_deactivating_the_active_trainer_moves_the_player_to_another(
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

    # Establish trainer_a as the active context.
    await app_client.put(
        "/me/context", json={"player_profile_id": profile.id, "trainer_id": trainer_a.id}
    )

    trainer_a.status = AccountStatus.INACTIVE.value
    await db_session.commit()

    response = await app_client.get("/me/contexts")
    body = response.json()
    assert body["active_trainer_id"] == trainer_b.id
    assert {c["trainer_id"] for c in body["contexts"]} == {trainer_b.id}


async def test_deactivating_every_trainer_leaves_a_valid_zero_trainer_state(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    await app_client.put(
        "/me/context", json={"player_profile_id": profile.id, "trainer_id": trainer.id}
    )

    trainer.status = AccountStatus.INACTIVE.value
    await db_session.commit()

    response = await app_client.get("/me/contexts")
    assert response.status_code == 200
    body = response.json()
    assert body["active_trainer_id"] is None
    assert body["active_player_profile_id"] is None
    assert body["contexts"] == []


async def test_reactivating_the_trainer_restores_the_switcher_entry(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    trainer.status = AccountStatus.INACTIVE.value
    await db_session.commit()
    await app_client.get("/me/contexts")  # repairs to zero-context state

    trainer.status = AccountStatus.ACTIVE.value
    await db_session.commit()

    response = await app_client.get("/me/contexts")
    body = response.json()
    assert body["active_trainer_id"] == trainer.id
    assert len(body["contexts"]) == 1
