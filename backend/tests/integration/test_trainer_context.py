from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.association import TrainerPlayerAssociation
from app.models.enums import UserRole
from tests.helpers import (
    create_player_with_detail,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def _associate(db_session: AsyncSession, *, trainer_id: str, player_id: str) -> None:
    db_session.add(
        TrainerPlayerAssociation(
            trainer_user_id=trainer_id, player_user_id=player_id, status="active"
        )
    )
    await db_session.flush()


async def test_switching_context_changes_active_trainer_id(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    trainer_b, _ = await create_trainer_with_link(db_session)
    player = await create_player_with_detail(db_session)
    await _associate(db_session, trainer_id=trainer_a.id, player_id=player.id)
    await _associate(db_session, trainer_id=trainer_b.id, player_id=player.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.put("/me/trainer-context", json={"trainer_id": trainer_b.id})

    assert response.status_code == 200
    body = response.json()
    assert body["active_trainer_id"] == trainer_b.id
    assert {t["trainer_id"] for t in body["trainers"]} == {trainer_a.id, trainer_b.id}


async def test_session_restores_last_used_context(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    trainer_b, _ = await create_trainer_with_link(db_session)
    player = await create_player_with_detail(db_session)
    await _associate(db_session, trainer_id=trainer_a.id, player_id=player.id)
    await _associate(db_session, trainer_id=trainer_b.id, player_id=player.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    await app_client.put("/me/trainer-context", json={"trainer_id": trainer_b.id})

    session_response = await app_client.get("/auth/session")
    assert session_response.status_code == 200
    assert session_response.json()["active_trainer_id"] == trainer_b.id
    assert session_response.json()["trainer_count"] == 2


async def test_switching_to_an_unassociated_trainer_returns_404_not_403(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    other_trainer, _ = await create_trainer_with_link(db_session)
    player = await create_player_with_detail(db_session)
    await _associate(db_session, trainer_id=trainer_a.id, player_id=player.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.put("/me/trainer-context", json={"trainer_id": other_trainer.id})

    assert response.status_code == 404
    assert response.json()["error"]["code"] != "forbidden"


async def test_a_player_with_one_trainer_has_no_switcher_signal(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    player = await create_player_with_detail(db_session)
    await _associate(db_session, trainer_id=trainer.id, player_id=player.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/me/trainers")

    assert response.status_code == 200
    body = response.json()
    assert len(body["trainers"]) == 1
    assert body["active_trainer_id"] == trainer.id


async def test_non_player_role_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    coach = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/me/trainers")
    assert response.status_code == 403
