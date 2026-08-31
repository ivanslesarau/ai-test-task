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
    my_profile = await create_player_profile(db_session, account=my_player, kind="self")
    other_player = await create_user(db_session, role=UserRole.PLAYER_PARENT, first_name="Theirs")
    other_profile = await create_player_profile(db_session, account=other_player, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=my_profile.id)
    await create_association(
        db_session, trainer_id=other_trainer.id, player_profile_id=other_profile.id
    )
    await db_session.commit()

    response = await app_client.get("/trainer/players")

    assert response.status_code == 200
    body = response.json()
    profile_ids = {item["player_profile_id"] for item in body["items"]}
    assert profile_ids == {my_profile.id}


async def test_response_names_nothing_about_other_trainers(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await _sign_in_trainer(app_client, db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)
    await db_session.commit()

    response = await app_client.get("/trainer/players")

    body = response.json()
    assert "trainer_id" not in body["items"][0]
    assert "trainer_count" not in body["items"][0]
    assert set(body["items"][0].keys()) == {
        "player_profile_id",
        "display_name",
        "kind",
        "age",
        "gender",
        "joined_at",
        "photo_url",
        "responsible_contact",
        # US5 (T607): the profile's stated week, embedded so the roster
        # renders it without one request per row (research.md R2-12) —
        # not a leak, since it names only this profile's own times.
        "availability",
        "availability_updated_at",
    }
    assert "id" not in body["items"][0]["responsible_contact"]


async def test_paging_and_name_filter(app_client: AsyncClient, db_session: AsyncSession) -> None:
    trainer, _ = await _sign_in_trainer(app_client, db_session)
    for i in range(3):
        p = await create_user(
            db_session, role=UserRole.PLAYER_PARENT, first_name=f"Player{i}", last_name="Test"
        )
        profile = await create_player_profile(db_session, account=p, kind="self")
        await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)
    await db_session.commit()

    page = await app_client.get("/trainer/players", params={"page": 1, "page_size": 2})
    assert page.status_code == 200
    assert len(page.json()["items"]) == 2
    assert page.json()["total"] == 3

    filtered = await app_client.get("/trainer/players", params={"q": "Player1"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1


async def test_child_profile_reveals_the_parents_contact(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """FR-116: a trainer with a child on their roster can reach the
    responsible parent, not the child, who has no contact of their own."""
    trainer, _ = await _sign_in_trainer(app_client, db_session)
    parent = await create_user(
        db_session, role=UserRole.PLAYER_PARENT, first_name="Jamie", last_name="Guardian"
    )
    child_profile = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Sam", last_name="Lee"
    )
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=child_profile.id)
    await db_session.commit()

    response = await app_client.get("/trainer/players")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["player_profile_id"] == child_profile.id
    assert item["display_name"] == "Sam Lee"
    assert item["kind"] == "child"
    assert item["responsible_contact"]["display_name"] == "Jamie Guardian"
    assert item["responsible_contact"]["email"] == parent.email


async def test_non_trainer_is_refused(app_client: AsyncClient, db_session: AsyncSession) -> None:
    coach = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/trainer/players")
    assert response.status_code == 403
