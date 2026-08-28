"""quickstart.md Story 9 scenarios 9.1-9.13 (US9, tasks.md T351)."""

import asyncio

from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.engine import _set_sqlite_pragmas
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.player_profile_repository import PlayerProfileRepository
from tests.helpers import (
    create_association,
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


def _child_body(**overrides: object) -> dict:
    body: dict[str, object] = {
        "first_name": "Riley",
        "last_name": "Jordan",
        "date_of_birth": "2016-01-01",
        "gender": "male",
    }
    body.update(overrides)
    return body


async def _sign_in_parent(db_session: AsyncSession, app_client: AsyncClient) -> User:
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return parent


# 9.1 ------------------------------------------------------------------------


async def test_adding_a_child_creates_it_marked_as_a_child(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_parent(db_session, app_client)

    response = await app_client.post("/me/players", json=_child_body())

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "child"
    assert body["display_name"] == "Riley Jordan"
    assert body["associations"] == []

    listed = await app_client.get("/me/players")
    assert listed.status_code == 200
    assert [p["id"] for p in listed.json()["profiles"]] == [body["id"]]


# 9.2 ------------------------------------------------------------------------


async def test_answering_yes_to_the_single_trainer_question_associates_the_child(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await _sign_in_parent(db_session, app_client)
    trainer, _ = await create_trainer_with_link(db_session)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=self_profile.id)
    await db_session.commit()

    response = await app_client.post("/me/players", json=_child_body(trainer_ids=[trainer.id]))

    assert response.status_code == 201
    body = response.json()
    assert [a["trainer_id"] for a in body["associations"]] == [trainer.id]

    trainer_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", trainer_token)
    roster = await app_client.get("/trainer/players")
    assert roster.status_code == 200
    assert body["id"] in {item["player_profile_id"] for item in roster.json()["items"]}


# 9.3 ------------------------------------------------------------------------


async def test_answering_no_creates_the_child_with_no_association(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await _sign_in_parent(db_session, app_client)
    trainer, _ = await create_trainer_with_link(db_session)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=self_profile.id)
    await db_session.commit()

    response = await app_client.post("/me/players", json=_child_body(trainer_ids=[]))

    assert response.status_code == 201
    assert response.json()["associations"] == []


# 9.4 ------------------------------------------------------------------------


async def test_selecting_two_of_three_trainers_associates_only_those_two(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await _sign_in_parent(db_session, app_client)
    trainer_a, _ = await create_trainer_with_link(db_session)
    trainer_b, _ = await create_trainer_with_link(db_session)
    trainer_c, _ = await create_trainer_with_link(db_session)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    for trainer in (trainer_a, trainer_b, trainer_c):
        await create_association(
            db_session, trainer_id=trainer.id, player_profile_id=self_profile.id
        )
    await db_session.commit()

    response = await app_client.post(
        "/me/players", json=_child_body(trainer_ids=[trainer_a.id, trainer_b.id])
    )

    assert response.status_code == 201
    associated = {a["trainer_id"] for a in response.json()["associations"]}
    assert associated == {trainer_a.id, trainer_b.id}


# 9.5 ------------------------------------------------------------------------


async def test_a_parent_with_no_trainer_adds_a_child_with_no_association(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_parent(db_session, app_client)

    response = await app_client.post("/me/players", json=_child_body())

    assert response.status_code == 201
    assert response.json()["associations"] == []


# 9.6 ------------------------------------------------------------------------


async def test_an_adult_date_of_birth_is_refused_on_the_field(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_parent(db_session, app_client)

    response = await app_client.post("/me/players", json=_child_body(date_of_birth="2000-01-01"))

    # A model-level validator (age-band-by-kind, matching JoinRegistrationRequest's
    # own precedent) reports 422 without a single offending field name.
    assert response.status_code == 422


# 9.7 ------------------------------------------------------------------------


async def test_missing_gender_is_refused(app_client: AsyncClient, db_session: AsyncSession) -> None:
    await _sign_in_parent(db_session, app_client)
    body = _child_body()
    del body["gender"]

    response = await app_client.post("/me/players", json=body)

    assert response.status_code == 422
    fields = {f["field"] for f in response.json()["error"]["fields"]}
    assert any("gender" in f for f in fields)


# 9.8 / 9.9 --------------------------------------------------------------


async def test_a_near_duplicate_child_is_refused_then_overrulable(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_parent(db_session, app_client)
    first = await app_client.post("/me/players", json=_child_body())
    assert first.status_code == 201

    duplicate = await app_client.post(
        "/me/players", json=_child_body(first_name="riley ", last_name=" JORDAN")
    )

    assert duplicate.status_code == 409
    body = duplicate.json()
    assert body["error"]["code"] == "possible_duplicate_profile"
    assert first.json()["id"] in {m["id"] for m in body["error"]["matches"]}

    overruled = await app_client.post(
        "/me/players",
        json=_child_body(
            first_name="riley ", last_name=" JORDAN", acknowledge_possible_duplicate=True
        ),
    )
    assert overruled.status_code == 201
    assert overruled.json()["id"] != first.json()["id"]


# 9.10 ------------------------------------------------------------------------


async def test_the_account_holders_own_profile_appears_alongside_children(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await _sign_in_parent(db_session, app_client)
    await create_player_profile(db_session, account=parent, kind="self")
    await db_session.commit()

    child = await app_client.post("/me/players", json=_child_body())
    assert child.status_code == 201

    listed = await app_client.get("/me/players")
    kinds = {p["kind"] for p in listed.json()["profiles"]}
    assert kinds == {"self", "child"}


# 9.11 ------------------------------------------------------------------------


async def test_a_second_self_profile_is_refused_even_when_raced(
    db_session: AsyncSession,
) -> None:
    """The partial unique index `uq_player_profiles_one_self`, not a
    service check, is what makes this true — proven by racing two
    concurrent inserts through two independent connections, which no
    single-session manual walk can do (research.md R-45 mirrors this
    shape for duplicate children; here it is FR-106's one-self rule,
    Story 9 scenario 8)."""
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    await db_session.commit()

    database_url = get_settings().database_url

    async def _insert_self() -> Exception | None:
        engine = create_async_engine(database_url)
        event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
        sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessionmaker() as session:
                repo = PlayerProfileRepository(session)
                await repo.insert(
                    account_user_id=parent.id,
                    kind="self",
                    first_name=None,
                    last_name=None,
                    date_of_birth=None,
                    gender=None,
                )
                await session.commit()
                return None
        except Exception as exc:  # noqa: BLE001 — the race's outcome is the point
            return exc
        finally:
            await engine.dispose()

    results = await asyncio.gather(_insert_self(), _insert_self())
    successes = [r for r in results if r is None]
    failures = [r for r in results if r is not None]
    assert len(successes) == 1
    assert len(failures) == 1


# 9.12 ------------------------------------------------------------------------


async def test_a_trainer_cannot_add_a_child(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post("/me/players", json=_child_body())

    assert response.status_code == 403


# 9.13 ------------------------------------------------------------------------


async def test_a_profile_on_another_account_is_404_not_403(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    other_parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    other_profile = await create_player_profile(db_session, account=other_parent, kind="self")
    await _sign_in_parent(db_session, app_client)
    await db_session.commit()

    response = await app_client.get(f"/me/players/{other_profile.id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] != "forbidden"


# --- update / remove / photo (T349, T350) -----------------------------------


async def test_updating_a_child_writes_the_field(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_parent(db_session, app_client)
    created = await app_client.post("/me/players", json=_child_body())
    profile_id = created.json()["id"]

    response = await app_client.patch(f"/me/players/{profile_id}", json={"school": "Riverside"})

    assert response.status_code == 200
    assert response.json()["school"] == "Riverside"


async def test_supplying_a_name_on_a_self_profile_is_422(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await _sign_in_parent(db_session, app_client)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    await db_session.commit()

    response = await app_client.patch(
        f"/me/players/{self_profile.id}", json={"school": "New School"}
    )
    assert response.status_code == 200

    refused = await app_client.patch(f"/me/players/{self_profile.id}", json={"first_name": "Nope"})
    assert refused.status_code == 422


async def test_removing_a_profile_is_soft_and_it_disappears_from_the_list(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_parent(db_session, app_client)
    created = await app_client.post("/me/players", json=_child_body())
    profile_id = created.json()["id"]

    response = await app_client.delete(f"/me/players/{profile_id}")
    assert response.status_code == 204

    listed = await app_client.get("/me/players")
    assert listed.json()["profiles"] == []

    fetched = await app_client.get(f"/me/players/{profile_id}")
    assert fetched.status_code == 404


async def test_uploading_a_photo_to_a_self_profile_is_422(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await _sign_in_parent(db_session, app_client)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    await db_session.commit()

    response = await app_client.put(
        f"/me/players/{self_profile.id}/photo",
        files={"file": ("photo.png", b"not-a-real-image", "image/png")},
    )

    assert response.status_code == 422


async def test_a_child_reaches_only_their_own_profile(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    sibling_a = await create_player_profile(
        db_session, account=parent, kind="child", first_name="A", last_name="Sib"
    )
    sibling_b_account = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    sibling_b = await create_player_profile(
        db_session,
        account=parent,
        kind="child",
        first_name="B",
        last_name="Sib",
        sign_in_user_id=sibling_b_account.id,
    )
    token = await create_session_cookie(db_session, sibling_b_account)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    own = await app_client.get(f"/me/players/{sibling_b.id}")
    assert own.status_code == 200

    other = await app_client.get(f"/me/players/{sibling_a.id}")
    assert other.status_code == 404

    listed = await app_client.get("/me/players")
    assert [p["id"] for p in listed.json()["profiles"]] == [sibling_b.id]
