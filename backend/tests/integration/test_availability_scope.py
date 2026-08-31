"""US3, FR-033, FR-036, tasks.md T571 — `/me/availability` is Coach-only,
and a coach cannot reach anyone else's week by any route."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.role_details import CoachDetail
from tests.helpers import create_session_cookie, create_user


async def _sign_in(app_client: AsyncClient, db_session: AsyncSession, role: UserRole) -> None:
    user = await create_user(db_session, role=role)
    if role is UserRole.COACH:
        db_session.add(CoachDetail(user_id=user.id, is_publicly_visible=False))
        await db_session.flush()
    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


@pytest.mark.parametrize("role", [UserRole.SUPER_ADMIN, UserRole.TRAINER, UserRole.PLAYER_PARENT])
async def test_non_coach_roles_cannot_reach_me_availability(
    app_client: AsyncClient, db_session: AsyncSession, role: UserRole
) -> None:
    await _sign_in(app_client, db_session, role)

    response = await app_client.get("/me/availability")

    assert response.status_code == 403


async def test_an_unauthenticated_caller_is_401(app_client: AsyncClient) -> None:
    response = await app_client.get("/me/availability")
    assert response.status_code == 401


async def test_a_second_coachs_week_is_not_reachable_through_me_availability(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """`/me/availability` names no id — a second coach's slots simply
    cannot be addressed through this route at all; each coach reads and
    writes only their own row set."""
    other_coach = await create_user(db_session, role=UserRole.COACH)
    db_session.add(CoachDetail(user_id=other_coach.id, is_publicly_visible=False))
    await db_session.flush()
    other_token = await create_session_cookie(db_session, other_coach)
    await db_session.commit()

    app_client.cookies.set("pp_session", other_token)
    saved = await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]},
    )
    assert saved.status_code == 200

    await _sign_in(app_client, db_session, UserRole.COACH)
    mine = await app_client.get("/me/availability")
    assert mine.json() == {"slots": [], "updated_at": None}
