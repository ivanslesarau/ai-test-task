"""quickstart.md §3.4 — a parent states a separate week per profile (US4,
FR-025, FR-033, SC-006, tasks.md T587)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User
from tests.helpers import create_player_profile, create_session_cookie, create_user


async def _sign_in(app_client: AsyncClient, db_session: AsyncSession, user: User) -> None:
    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


async def test_saving_one_childs_week_leaves_a_siblings_and_the_parents_own_untouched(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    grace = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Grace", last_name="Family"
    )
    leo = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Leo", last_name="Family"
    )
    await db_session.commit()
    await _sign_in(app_client, db_session, parent)

    grace_save = await app_client.put(
        f"/me/players/{grace.id}/availability",
        json={"slots": [{"day_of_week": 1, "start_minute": 1020, "end_minute": 1200}]},
    )
    assert grace_save.status_code == 200

    leo_save = await app_client.put(
        f"/me/players/{leo.id}/availability",
        json={"slots": [{"day_of_week": 5, "start_minute": 540, "end_minute": 720}]},
    )
    assert leo_save.status_code == 200

    grace_read = await app_client.get(f"/me/players/{grace.id}/availability")
    assert grace_read.json()["slots"] == [
        {"day_of_week": 1, "start_minute": 1020, "end_minute": 1200}
    ]

    leo_read = await app_client.get(f"/me/players/{leo.id}/availability")
    assert leo_read.json()["slots"] == [{"day_of_week": 5, "start_minute": 540, "end_minute": 720}]

    self_read = await app_client.get(f"/me/players/{self_profile.id}/availability")
    assert self_read.json() == {"slots": [], "updated_at": None}


async def test_the_parent_may_state_their_own_profiles_week_too(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    await db_session.commit()
    await _sign_in(app_client, db_session, parent)

    response = await app_client.put(
        f"/me/players/{self_profile.id}/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]},
    )

    assert response.status_code == 200
    assert response.json()["slots"] == [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]


async def test_the_parent_may_revise_what_a_child_stated(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    grace = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Grace", last_name="Family"
    )
    await db_session.commit()
    await _sign_in(app_client, db_session, parent)

    await app_client.put(
        f"/me/players/{grace.id}/availability",
        json={"slots": [{"day_of_week": 1, "start_minute": 600, "end_minute": 660}]},
    )
    revised = await app_client.put(
        f"/me/players/{grace.id}/availability",
        json={"slots": [{"day_of_week": 2, "start_minute": 600, "end_minute": 660}]},
    )

    assert revised.status_code == 200
    assert [s["day_of_week"] for s in revised.json()["slots"]] == [2]
