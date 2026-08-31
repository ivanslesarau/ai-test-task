"""Constitution's field-clearing gate, applied to availability (tasks.md
T600): an empty `slots` array clears the week and stamps `updated_at`; a
malformed body leaves it untouched. `AvailabilityWeekUpdate` has no
optional/nullable scalar field of its own — the whole payload IS the
value, so "clearing" here is the `slots: []` / `DELETE` semantics FR-030
and FR-032 define, and "the key absent" is the malformed-body case that
must change nothing (mirroring FR-027/SC-008's byte-identical guarantee)."""

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


async def test_an_empty_slots_array_clears_the_week_and_stamps_updated_at(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_coach(app_client, db_session)
    await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]},
    )

    response = await app_client.put("/me/availability", json={"slots": []})

    assert response.status_code == 200
    body = response.json()
    assert body["slots"] == []
    assert body["updated_at"] is not None


async def test_a_malformed_body_is_refused_and_leaves_the_stored_week_unchanged(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_coach(app_client, db_session)
    baseline = {"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]}
    seeded = await app_client.put("/me/availability", json=baseline)
    assert seeded.status_code == 200

    # Missing the required `slots` key entirely — refused before it ever
    # reaches the service.
    malformed = await app_client.put("/me/availability", json={})
    assert malformed.status_code == 422

    unchanged = await app_client.get("/me/availability")
    assert unchanged.json()["slots"] == baseline["slots"]
