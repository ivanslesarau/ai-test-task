"""US6 (tasks.md T615, FR-043, SC-016): the single most important
correctness property in this phase — while impersonating, the effective
user's capabilities are EXACTLY the target's. Every `/admin/**` route
403s, the target's own routes work normally, and the data returned is
the target's own — for each of the three impersonable roles.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.role_details import CoachDetail
from tests.helpers import create_coach_invitation, create_family, create_session_cookie, create_user


async def _sign_in_admin(app_client: AsyncClient, db_session: AsyncSession) -> str:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return admin.id


async def test_impersonating_a_trainer_reaches_no_admin_route_but_their_own(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    invitation, _ = await create_coach_invitation(db_session, trainer=trainer)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    admin_route = await app_client.get("/admin/users")
    assert admin_route.status_code == 403

    own_route = await app_client.get("/trainer/players")
    assert own_route.status_code == 200

    invitations = await app_client.get("/trainer/coach-invitations")
    assert invitations.status_code == 200
    assert {row["id"] for row in invitations.json()["items"]} == {invitation.id}


async def test_impersonating_a_coach_reaches_no_admin_route_but_their_own(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    coach = await create_user(db_session, role=UserRole.COACH)
    db_session.add(CoachDetail(user_id=coach.id, is_publicly_visible=False))
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": coach.id})
    assert started.status_code == 201

    admin_route = await app_client.get("/admin/users")
    assert admin_route.status_code == 403

    saved = await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 1, "start_minute": 540, "end_minute": 600}]},
    )
    assert saved.status_code == 200

    week = await app_client.get("/me/availability")
    assert week.status_code == 200
    assert week.json()["slots"] == [{"day_of_week": 1, "start_minute": 540, "end_minute": 600}]


async def test_impersonating_a_player_parent_reaches_no_admin_route_but_their_own(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    parent, profiles, _ = await create_family(db_session, children=1)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": parent.id})
    assert started.status_code == 201

    admin_route = await app_client.get("/admin/users")
    assert admin_route.status_code == 403

    own_route = await app_client.get("/me/players")
    assert own_route.status_code == 200
    assert {row["id"] for row in own_route.json()["profiles"]} == {profiles[0].id}
