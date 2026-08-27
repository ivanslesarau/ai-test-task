from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.association import TrainerPlayerAssociation
from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_trainer_with_link, create_user


async def _associate(db_session: AsyncSession, *, trainer_id: str, player_id: str) -> None:
    db_session.add(
        TrainerPlayerAssociation(
            trainer_user_id=trainer_id, player_user_id=player_id, status="active"
        )
    )
    await db_session.flush()


async def _sign_in_trainer(app_client: AsyncClient, db_session: AsyncSession):
    trainer, link = await create_trainer_with_link(db_session)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return trainer, link


async def test_trainer_sees_only_their_own_players(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await _sign_in_trainer(app_client, db_session)
    other_trainer, _ = await create_trainer_with_link(db_session)

    my_player = await create_user(db_session, role=UserRole.PLAYER_PARENT, first_name="Mine")
    other_player = await create_user(db_session, role=UserRole.PLAYER_PARENT, first_name="Theirs")
    await _associate(db_session, trainer_id=trainer.id, player_id=my_player.id)
    await _associate(db_session, trainer_id=other_trainer.id, player_id=other_player.id)
    await db_session.commit()

    response = await app_client.get("/trainer/players")

    assert response.status_code == 200
    body = response.json()
    names = {item["player_user_id"] for item in body["items"]}
    assert names == {my_player.id}


async def test_response_names_nothing_about_other_trainers(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await _sign_in_trainer(app_client, db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    await _associate(db_session, trainer_id=trainer.id, player_id=player.id)
    await db_session.commit()

    response = await app_client.get("/trainer/players")

    body = response.json()
    assert "trainer_id" not in body["items"][0]
    assert "trainer_count" not in body["items"][0]
    assert set(body["items"][0].keys()) == {
        "player_user_id",
        "display_name",
        "is_self",
        "age",
        "gender",
        "joined_at",
        "photo_url",
    }


async def test_paging_and_name_filter(app_client: AsyncClient, db_session: AsyncSession) -> None:
    trainer, _ = await _sign_in_trainer(app_client, db_session)
    for i in range(3):
        p = await create_user(
            db_session, role=UserRole.PLAYER_PARENT, first_name=f"Player{i}", last_name="Test"
        )
        await _associate(db_session, trainer_id=trainer.id, player_id=p.id)
    await db_session.commit()

    page = await app_client.get("/trainer/players", params={"page": 1, "page_size": 2})
    assert page.status_code == 200
    assert len(page.json()["items"]) == 2
    assert page.json()["total"] == 3

    filtered = await app_client.get("/trainer/players", params={"q": "Player1"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1


async def test_non_trainer_is_refused(app_client: AsyncClient, db_session: AsyncSession) -> None:
    coach = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/trainer/players")
    assert response.status_code == 403
