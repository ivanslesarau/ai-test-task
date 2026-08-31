"""quickstart.md Story 13 scenarios 13.1-13.9 (US13, tasks.md T415, FR-068,
FR-082, FR-122)."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.association import TrainerPlayerAssociation
from app.models.enums import UserRole
from tests.helpers import (
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def _family_of_three(db_session: AsyncSession):
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    child_one = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Alex", last_name="Family"
    )
    child_two = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Maya", last_name="Family"
    )
    return parent, self_profile, child_one, child_two


async def test_the_question_is_offered_with_every_family_member_when_children_exist(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """13.1."""
    parent, self_profile, child_one, child_two = await _family_of_three(db_session)
    _, link = await create_trainer_with_link(db_session, business_name="Third Academy")
    await db_session.commit()

    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    preview = await app_client.get(f"/join/{link.code}")
    assert preview.status_code == 200
    viewer = preview.json()["viewer"]
    assert viewer["state"] == "choose_family_members"
    offered_ids = {p["player_profile_id"] for p in viewer["selectable_profiles"]}
    assert offered_ids == {self_profile.id, child_one.id, child_two.id}
    assert all(p["already_associated"] is False for p in viewer["selectable_profiles"])


async def test_selecting_two_of_three_associates_exactly_those_two(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """13.2, 13.3, 13.8."""
    parent, self_profile, child_one, child_two = await _family_of_three(db_session)
    _, link = await create_trainer_with_link(db_session, business_name="Third Academy")
    await db_session.commit()

    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(
        f"/join/{link.code}/accept",
        json={"player_profile_ids": [self_profile.id, child_one.id]},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body["associated_profile_ids"]) == {self_profile.id, child_one.id}
    assert body["already_associated_profile_ids"] == []
    # 13.8 — the account holder's own profile, since it was selected.
    assert body["active_player_profile_id"] == self_profile.id
    assert body["active_trainer_id"] is not None

    associated = (
        (
            await db_session.execute(
                select(TrainerPlayerAssociation.player_profile_id).where(
                    TrainerPlayerAssociation.trainer_user_id == body["trainer_id"]
                )
            )
        )
        .scalars()
        .all()
    )
    assert set(associated) == {self_profile.id, child_one.id}
    assert child_two.id not in associated

    # 13.3 — the link's use count rose by exactly 2.
    await db_session.refresh(link)
    assert link.use_count == 2


async def test_selecting_only_a_child_makes_that_child_the_active_context(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """13.9."""
    parent, self_profile, child_one, child_two = await _family_of_three(db_session)
    _, link = await create_trainer_with_link(db_session, business_name="Third Academy")
    await db_session.commit()

    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(
        f"/join/{link.code}/accept", json={"player_profile_ids": [child_one.id]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["active_player_profile_id"] == child_one.id


async def test_selecting_nobody_changes_nothing(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """13.4."""
    parent, _self_profile, _child_one, _child_two = await _family_of_three(db_session)
    _, link = await create_trainer_with_link(db_session, business_name="Third Academy")
    await db_session.commit()

    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/join/{link.code}/accept", json={"player_profile_ids": []})
    assert response.status_code == 200
    body = response.json()
    assert body["associated_profile_ids"] == []
    assert body["already_associated_profile_ids"] == []
    assert body["active_player_profile_id"] is None
    assert body["active_trainer_id"] is None

    result = await db_session.execute(select(TrainerPlayerAssociation))
    assert result.scalars().all() == []

    await db_session.refresh(link)
    assert link.use_count == 0


async def test_a_parent_with_no_children_sees_the_ordinary_single_profile_flow(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """13.5 — the no-children case is unchanged from US7."""
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    trainer, link = await create_trainer_with_link(db_session, business_name="Solo Academy")
    await db_session.commit()

    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    preview = await app_client.get(f"/join/{link.code}")
    assert preview.status_code == 200
    assert preview.json()["viewer"]["state"] == "can_join"

    response = await app_client.post(f"/join/{link.code}/accept")
    assert response.status_code == 200
    body = response.json()
    assert body["associated_profile_ids"] == [self_profile.id]
    assert body["active_player_profile_id"] == self_profile.id
    assert body["active_trainer_id"] == trainer.id


async def test_reopening_the_link_marks_joined_profiles_connected_and_unselectable(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """13.6, 13.7."""
    parent, self_profile, child_one, child_two = await _family_of_three(db_session)
    _, link = await create_trainer_with_link(db_session, business_name="Third Academy")
    await db_session.commit()

    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    first = await app_client.post(
        f"/join/{link.code}/accept",
        json={"player_profile_ids": [self_profile.id, child_one.id]},
    )
    assert first.status_code == 200

    # 13.6 — re-open the link: the two joined profiles show connected.
    preview = await app_client.get(f"/join/{link.code}")
    by_id = {p["player_profile_id"]: p for p in preview.json()["viewer"]["selectable_profiles"]}
    assert by_id[self_profile.id]["already_associated"] is True
    assert by_id[child_one.id]["already_associated"] is True
    assert by_id[child_two.id]["already_associated"] is False

    # 13.7 — selecting the remaining child (plus the two already-joined,
    # which must cost nothing) raises the use count by exactly 1.
    second = await app_client.post(
        f"/join/{link.code}/accept",
        json={"player_profile_ids": [self_profile.id, child_one.id, child_two.id]},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["associated_profile_ids"] == [child_two.id]
    assert set(body["already_associated_profile_ids"]) == {self_profile.id, child_one.id}

    await db_session.refresh(link)
    assert link.use_count == 3
