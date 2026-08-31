"""quickstart.md §3.2 — a refused save leaves the stored week byte-identical
(US3, FR-027, SC-008, tasks.md T569)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.role_details import CoachDetail
from tests.helpers import create_session_cookie, create_user

_BASELINE = {
    "slots": [
        {"day_of_week": 0, "start_minute": 960, "end_minute": 1080},
        {"day_of_week": 0, "start_minute": 1140, "end_minute": 1260},
        {"day_of_week": 5, "start_minute": 540, "end_minute": 720},
    ]
}


async def _coach_with_baseline(app_client: AsyncClient, db_session: AsyncSession) -> None:
    coach = await create_user(db_session, role=UserRole.COACH)
    db_session.add(CoachDetail(user_id=coach.id, is_publicly_visible=False))
    await db_session.flush()
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    seeded = await app_client.put("/me/availability", json=_BASELINE)
    assert seeded.status_code == 200


async def _assert_unchanged(app_client: AsyncClient) -> None:
    current = await app_client.get("/me/availability")
    assert current.status_code == 200
    body = current.json()
    assert [(s["day_of_week"], s["start_minute"], s["end_minute"]) for s in body["slots"]] == [
        (0, 960, 1080),
        (0, 1140, 1260),
        (5, 540, 720),
    ]


async def test_overlapping_ranges_are_refused_and_the_day_named_and_nothing_changes(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _coach_with_baseline(app_client, db_session)

    response = await app_client.put(
        "/me/availability",
        json={
            "slots": [
                {"day_of_week": 1, "start_minute": 540, "end_minute": 660},
                {"day_of_week": 1, "start_minute": 600, "end_minute": 720},
            ]
        },
    )

    assert response.status_code == 422
    fields = {f["field"] for f in response.json()["error"]["fields"]}
    assert "1" in fields
    await _assert_unchanged(app_client)


async def test_more_than_six_ranges_in_a_day_is_refused_and_nothing_changes(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _coach_with_baseline(app_client, db_session)

    slots = [
        {"day_of_week": 2, "start_minute": i * 60, "end_minute": i * 60 + 30} for i in range(7)
    ]
    response = await app_client.put("/me/availability", json={"slots": slots})

    assert response.status_code == 422
    fields = {f["field"] for f in response.json()["error"]["fields"]}
    assert "2" in fields
    await _assert_unchanged(app_client)


async def test_a_start_at_or_after_its_end_is_refused_on_the_field_and_nothing_changes(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _coach_with_baseline(app_client, db_session)

    response = await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 4, "start_minute": 600, "end_minute": 600}]},
    )

    assert response.status_code == 422
    await _assert_unchanged(app_client)


async def test_an_off_grid_time_is_refused_and_nothing_changes(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _coach_with_baseline(app_client, db_session)

    response = await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 4, "start_minute": 545, "end_minute": 600}]},
    )

    assert response.status_code == 422
    await _assert_unchanged(app_client)


async def test_a_range_past_midnight_is_refused_and_nothing_changes(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _coach_with_baseline(app_client, db_session)

    response = await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 4, "start_minute": 1425, "end_minute": 1470}]},
    )

    assert response.status_code == 422
    await _assert_unchanged(app_client)
