"""US7 (tasks.md T644): the impersonation history — every impersonation
appears once with both participants, times, duration, and end reason;
an in-progress one carries no duration; the four filters each return
exactly their subset (FR-053, FR-054).
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def _sign_in_admin(app_client: AsyncClient, db_session: AsyncSession) -> object:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return admin


async def test_a_completed_impersonation_appears_once_with_full_detail(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201
    ended = await app_client.delete("/admin/impersonations/current")
    assert ended.status_code == 204

    history = await app_client.get("/admin/impersonations")

    assert history.status_code == 200
    body = history.json()
    assert body["total"] == 1
    row = body["items"][0]
    assert row["admin"]["role"] == "super_admin"
    assert row["target"]["user_id"] == trainer.id
    assert row["ended_at"] is not None
    assert row["end_reason"] == "exited"
    assert row["duration_seconds"] is not None
    assert row["duration_seconds"] >= 0


async def test_an_in_progress_impersonation_shows_no_end_or_duration(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """The admin who is *mid-impersonation* cannot check the history
    themselves — their own effective user is the target, so `/admin/**`
    is rightly unreachable to them (FR-043) — so a second Super Admin
    reads it instead."""
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    other_admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    other_token = await create_session_cookie(db_session, other_admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", other_token)

    history = await app_client.get("/admin/impersonations")

    assert history.status_code == 200
    row = history.json()["items"][0]
    assert row["ended_at"] is None
    assert row["end_reason"] is None
    assert row["duration_seconds"] is None


async def test_filtering_by_admin_target_and_date_range(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin_a = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_b = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    target_x = await create_user(db_session, role=UserRole.TRAINER)
    target_y = await create_user(db_session, role=UserRole.COACH)
    token_a = await create_session_cookie(db_session, admin_a)
    token_b = await create_session_cookie(db_session, admin_b)
    await db_session.commit()

    app_client.cookies.set("pp_session", token_a)
    r1 = await app_client.post("/admin/impersonations", json={"user_id": target_x.id})
    assert r1.status_code == 201
    await app_client.delete("/admin/impersonations/current")

    app_client.cookies.set("pp_session", token_b)
    r2 = await app_client.post("/admin/impersonations", json={"user_id": target_y.id})
    assert r2.status_code == 201
    await app_client.delete("/admin/impersonations/current")

    by_admin = await app_client.get("/admin/impersonations", params={"admin_user_id": admin_a.id})
    assert by_admin.status_code == 200
    assert {row["target"]["user_id"] for row in by_admin.json()["items"]} == {target_x.id}

    by_target = await app_client.get(
        "/admin/impersonations", params={"target_user_id": target_y.id}
    )
    assert by_target.status_code == 200
    assert {row["admin"]["user_id"] for row in by_target.json()["items"]} == {admin_b.id}

    far_future = utcnow().replace(year=utcnow().year + 1).isoformat()
    by_date_none = await app_client.get(
        "/admin/impersonations", params={"started_from": far_future}
    )
    assert by_date_none.status_code == 200
    assert by_date_none.json()["total"] == 0

    all_rows = await app_client.get("/admin/impersonations")
    assert all_rows.status_code == 200
    assert all_rows.json()["total"] == 2
