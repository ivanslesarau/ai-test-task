"""quickstart.md Story 10 scenarios 10.1-10.11 (US10, tasks.md T354)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AssociationStatus, UserRole
from app.models.player_profile import PlayerProfile
from app.models.share_link import ShareLink
from app.models.user import User
from app.repositories.association_repository import AssociationRepository
from tests.helpers import (
    create_association,
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def _family_fixture(
    db_session: AsyncSession,
) -> tuple[User, User, User, ShareLink, PlayerProfile]:
    """A parent associated with two trainers and one child associated with
    one of them — this story's stated setup."""
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    trainer_a, link_a = await create_trainer_with_link(db_session)
    trainer_b, link_b = await create_trainer_with_link(db_session)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    await create_association(db_session, trainer_id=trainer_a.id, player_profile_id=self_profile.id)
    await create_association(db_session, trainer_id=trainer_b.id, player_profile_id=self_profile.id)
    child = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Kid", last_name="One"
    )
    await create_association(db_session, trainer_id=trainer_a.id, player_profile_id=child.id)
    return parent, trainer_a, trainer_b, link_b, child


async def _sign_in(db_session: AsyncSession, app_client: AsyncClient, user: User) -> None:
    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


# 10.1 ------------------------------------------------------------------------


async def test_listing_players_shows_each_ones_trainers_with_join_dates(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, trainer_a, _trainer_b, _link_b, child = await _family_fixture(db_session)
    await _sign_in(db_session, app_client, parent)

    response = await app_client.get("/me/players")

    assert response.status_code == 200
    child_row = next(p for p in response.json()["profiles"] if p["id"] == child.id)
    assert [a["trainer_id"] for a in child_row["associations"]] == [trainer_a.id]
    assert child_row["associations"][0]["joined_at"]


# 10.2 ------------------------------------------------------------------------


async def test_adding_the_second_trainer_by_trainer_id(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, _trainer_a, trainer_b, _link_b, child = await _family_fixture(db_session)
    await _sign_in(db_session, app_client, parent)

    response = await app_client.post(
        f"/me/players/{child.id}/trainers", json={"trainer_id": trainer_b.id}
    )

    assert response.status_code == 200
    trainer_ids = {a["trainer_id"] for a in response.json()["associations"]}
    assert trainer_ids == {_trainer_a.id, trainer_b.id}

    await _sign_in(db_session, app_client, trainer_b)
    roster = await app_client.get("/trainer/players")
    assert child.id in {item["player_profile_id"] for item in roster.json()["items"]}


# 10.3 ------------------------------------------------------------------------


async def test_adding_a_trainer_by_invitation_code(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, trainer_a, trainer_b, link_b, child = await _family_fixture(db_session)
    await _sign_in(db_session, app_client, parent)

    response = await app_client.post(f"/me/players/{child.id}/trainers", json={"code": link_b.code})

    assert response.status_code == 200
    trainer_ids = {a["trainer_id"] for a in response.json()["associations"]}
    assert trainer_ids == {trainer_a.id, trainer_b.id}


async def test_adding_a_trainer_by_invalid_code_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, _trainer_a, _trainer_b, _link_b, child = await _family_fixture(db_session)
    await _sign_in(db_session, app_client, parent)

    response = await app_client.post(
        f"/me/players/{child.id}/trainers", json={"code": "not-a-real-code-at-all"}
    )

    assert response.status_code == 404


# 10.4 ------------------------------------------------------------------------


async def test_sending_both_code_and_trainer_id_is_422(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, trainer_a, _trainer_b, link_b, child = await _family_fixture(db_session)
    await _sign_in(db_session, app_client, parent)

    response = await app_client.post(
        f"/me/players/{child.id}/trainers",
        json={"code": link_b.code, "trainer_id": trainer_a.id},
    )

    assert response.status_code == 422


async def test_sending_neither_code_nor_trainer_id_is_422(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, _trainer_a, _trainer_b, _link_b, child = await _family_fixture(db_session)
    await _sign_in(db_session, app_client, parent)

    response = await app_client.post(f"/me/players/{child.id}/trainers", json={})

    assert response.status_code == 422


# 10.5 ------------------------------------------------------------------------


async def test_adding_an_already_associated_trainer_is_a_no_op(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, trainer_a, _trainer_b, _link_b, child = await _family_fixture(db_session)
    await _sign_in(db_session, app_client, parent)

    response = await app_client.post(
        f"/me/players/{child.id}/trainers", json={"trainer_id": trainer_a.id}
    )

    assert response.status_code == 200
    assert [a["trainer_id"] for a in response.json()["associations"]] == [trainer_a.id]


# 10.6 / 10.7 ------------------------------------------------------------------


async def test_removing_an_association_hides_it_from_the_roster_but_keeps_history(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, trainer_a, _trainer_b, _link_b, child = await _family_fixture(db_session)
    await _sign_in(db_session, app_client, parent)

    profile_response = await app_client.get(f"/me/players/{child.id}")
    association_id = profile_response.json()["associations"][0]["association_id"]

    response = await app_client.delete(f"/me/players/{child.id}/trainers/{association_id}")
    assert response.status_code == 204

    await _sign_in(db_session, app_client, trainer_a)
    roster = await app_client.get("/trainer/players")
    assert child.id not in {item["player_profile_id"] for item in roster.json()["items"]}

    association = await AssociationRepository(db_session).get_by_id(association_id)
    assert association is not None
    assert association.status == AssociationStatus.INACTIVE.value


# 10.8 ------------------------------------------------------------------------


async def test_re_adding_a_removed_trainer_reuses_the_same_association(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, trainer_a, _trainer_b, _link_b, child = await _family_fixture(db_session)
    await _sign_in(db_session, app_client, parent)

    profile_response = await app_client.get(f"/me/players/{child.id}")
    association_id = profile_response.json()["associations"][0]["association_id"]
    await app_client.delete(f"/me/players/{child.id}/trainers/{association_id}")

    response = await app_client.post(
        f"/me/players/{child.id}/trainers", json={"trainer_id": trainer_a.id}
    )

    assert response.status_code == 200
    assert response.json()["associations"][0]["association_id"] == association_id

    association = await AssociationRepository(db_session).get_by_id(association_id)
    assert association is not None
    assert association.status == AssociationStatus.ACTIVE.value


# 10.9 ------------------------------------------------------------------------


async def test_removing_the_last_association_leaves_the_profile_with_none(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, _trainer_a, _trainer_b, _link_b, child = await _family_fixture(db_session)
    await _sign_in(db_session, app_client, parent)

    profile_response = await app_client.get(f"/me/players/{child.id}")
    association_id = profile_response.json()["associations"][0]["association_id"]

    response = await app_client.delete(f"/me/players/{child.id}/trainers/{association_id}")
    assert response.status_code == 204

    after = await app_client.get(f"/me/players/{child.id}")
    assert after.status_code == 200
    assert after.json()["associations"] == []


# 10.10 -----------------------------------------------------------------------


async def test_a_signed_in_child_cannot_add_or_remove_their_own_association(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    trainer_a, _link_a = await create_trainer_with_link(db_session)
    trainer_b, _link_b = await create_trainer_with_link(db_session)
    child_account = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    child = await create_player_profile(
        db_session,
        account=parent,
        kind="child",
        first_name="Kid",
        last_name="Two",
        sign_in_user_id=child_account.id,
    )
    association = await create_association(
        db_session, trainer_id=trainer_a.id, player_profile_id=child.id
    )
    await _sign_in(db_session, app_client, child_account)

    add_response = await app_client.post(
        f"/me/players/{child.id}/trainers", json={"trainer_id": trainer_b.id}
    )
    assert add_response.status_code == 403

    remove_response = await app_client.delete(f"/me/players/{child.id}/trainers/{association.id}")
    assert remove_response.status_code == 403


# 10.11 -----------------------------------------------------------------------


async def test_removing_an_association_on_another_accounts_profile_is_404(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _parent, trainer_a, _trainer_b, _link_b, child = await _family_fixture(db_session)
    other_parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)

    # The child's own association, fetched directly — `other_parent` may
    # not reach `child`'s profile through the API to discover it (that is
    # exactly the 404 this test proves).
    associations = await AssociationRepository(db_session).list_active_for_player(child.id)
    association_id = next(
        a.id for a, _trainer, _profile in associations if a.trainer_user_id == trainer_a.id
    )

    await _sign_in(db_session, app_client, other_parent)

    response = await app_client.delete(f"/me/players/{child.id}/trainers/{association_id}")

    assert response.status_code == 404
