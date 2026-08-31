"""quickstart.md §3.5 — sibling and account isolation (US4, FR-033, FR-036,
SC-009, tasks.md T588)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User
from tests.helpers import create_player_profile, create_session_cookie, create_user


async def _sign_in(app_client: AsyncClient, db_session: AsyncSession, user: User) -> None:
    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


async def test_a_signed_in_child_reaches_only_their_own_profile(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    grace_account = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    grace = await create_player_profile(
        db_session,
        account=parent,
        kind="child",
        first_name="Grace",
        last_name="Family",
        sign_in_user_id=grace_account.id,
    )
    leo = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Leo", last_name="Family"
    )
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    await db_session.commit()
    await _sign_in(app_client, db_session, grace_account)

    own_get = await app_client.get(f"/me/players/{grace.id}/availability")
    assert own_get.status_code == 200

    own_put = await app_client.put(
        f"/me/players/{grace.id}/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]},
    )
    assert own_put.status_code == 200

    sibling_get = await app_client.get(f"/me/players/{leo.id}/availability")
    assert sibling_get.status_code == 404

    sibling_put = await app_client.put(
        f"/me/players/{leo.id}/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]},
    )
    assert sibling_put.status_code == 404

    parent_own_get = await app_client.get(f"/me/players/{self_profile.id}/availability")
    assert parent_own_get.status_code == 404


async def test_an_unrelated_account_gets_404(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=parent, kind="self")
    stranger = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    await db_session.commit()
    await _sign_in(app_client, db_session, stranger)

    response = await app_client.get(f"/me/players/{profile.id}/availability")

    assert response.status_code == 404
    assert response.json()["error"]["code"] != "forbidden"


async def test_a_nonexistent_profile_id_is_404(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    await db_session.commit()
    await _sign_in(app_client, db_session, parent)

    response = await app_client.get("/me/players/does-not-exist/availability")

    assert response.status_code == 404
