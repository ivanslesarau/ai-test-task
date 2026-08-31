"""quickstart.md §3.1-3.2 — a coach's own week (US3, FR-024, FR-026 - FR-029,
FR-032, tasks.md T568)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.role_details import CoachDetail
from app.models.user import User
from tests.helpers import create_session_cookie, create_user


async def _sign_in_coach(app_client: AsyncClient, db_session: AsyncSession) -> User:
    coach = await create_user(db_session, role=UserRole.COACH)
    db_session.add(CoachDetail(user_id=coach.id, is_publicly_visible=False))
    await db_session.flush()
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return coach


async def test_never_stated_reads_as_empty_slots_and_null_updated_at(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_coach(app_client, db_session)

    response = await app_client.get("/me/availability")

    assert response.status_code == 200
    assert response.json() == {"slots": [], "updated_at": None}


async def test_saving_returns_the_week_ordered_by_day_then_start(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_coach(app_client, db_session)

    response = await app_client.put(
        "/me/availability",
        json={
            "slots": [
                {"day_of_week": 0, "start_minute": 1140, "end_minute": 1260},
                {"day_of_week": 0, "start_minute": 960, "end_minute": 1080},
                {"day_of_week": 5, "start_minute": 540, "end_minute": 720},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["updated_at"] is not None
    assert [(s["day_of_week"], s["start_minute"]) for s in body["slots"]] == [
        (0, 960),
        (0, 1140),
        (5, 540),
    ]


async def test_two_non_overlapping_ranges_on_one_day_both_persist(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_coach(app_client, db_session)

    response = await app_client.put(
        "/me/availability",
        json={
            "slots": [
                {"day_of_week": 0, "start_minute": 960, "end_minute": 1080},
                {"day_of_week": 0, "start_minute": 1140, "end_minute": 1260},
            ]
        },
    )

    assert response.status_code == 200
    assert len(response.json()["slots"]) == 2


async def test_the_week_survives_a_sign_out_sign_in_round_trip(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """SC-007."""
    coach = await _sign_in_coach(app_client, db_session)
    saved = await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 2, "start_minute": 600, "end_minute": 660}]},
    )
    assert saved.status_code == 200

    app_client.cookies.clear()
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/me/availability")
    assert response.status_code == 200
    assert response.json()["slots"] == [{"day_of_week": 2, "start_minute": 600, "end_minute": 660}]


async def test_a_second_save_replaces_the_week_wholesale(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_coach(app_client, db_session)
    await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]},
    )

    response = await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 3, "start_minute": 540, "end_minute": 600}]},
    )

    assert response.status_code == 200
    assert [s["day_of_week"] for s in response.json()["slots"]] == [3]
