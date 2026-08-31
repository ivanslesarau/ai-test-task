"""quickstart.md §3.3 — clearing is not the same as never having stated
(US3, FR-030, FR-032, FR-035, tasks.md T570)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.role_details import CoachDetail
from tests.helpers import create_session_cookie, create_user


async def _sign_in_coach(app_client: AsyncClient, db_session: AsyncSession) -> None:
    coach = await create_user(db_session, role=UserRole.COACH)
    db_session.add(CoachDetail(user_id=coach.id, is_publicly_visible=False))
    await db_session.flush()
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


async def test_clearing_a_stated_week_returns_204_and_stamps_a_non_null_updated_at(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_coach(app_client, db_session)
    await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]},
    )

    response = await app_client.delete("/me/availability")
    assert response.status_code == 204

    after = await app_client.get("/me/availability")
    body = after.json()
    assert body["slots"] == []
    assert body["updated_at"] is not None


async def test_a_never_stated_week_and_a_cleared_week_are_both_no_times_set_but_distinct(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_coach(app_client, db_session)

    never_stated = await app_client.get("/me/availability")
    assert never_stated.json() == {"slots": [], "updated_at": None}

    await app_client.delete("/me/availability")

    cleared = await app_client.get("/me/availability")
    assert cleared.json()["slots"] == []
    assert cleared.json()["updated_at"] is not None
    assert cleared.json()["updated_at"] != never_stated.json()["updated_at"]


async def test_clearing_an_already_empty_week_still_stamps_updated_at(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_coach(app_client, db_session)

    response = await app_client.delete("/me/availability")
    assert response.status_code == 204

    after = await app_client.get("/me/availability")
    assert after.json()["slots"] == []
    assert after.json()["updated_at"] is not None
