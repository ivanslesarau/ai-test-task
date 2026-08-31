"""US6 (tasks.md T614): starting an impersonation — 201, `/auth/session`
then describes the target with an `impersonation` block, the same
cookie resolves to the target, and a second start supersedes the first
(FR-040 – FR-043, FR-048).
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def _sign_in_admin(app_client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


async def test_starting_an_impersonation_returns_201_with_the_impersonation_shape(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    response = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})

    assert response.status_code == 201
    body = response.json()
    assert body["target"]["user_id"] == trainer.id
    assert body["target"]["role"] == "trainer"
    assert body["target_status_at_start"] == "active"
    assert body["ended_at"] is None
    assert body["end_reason"] is None
    assert body["duration_seconds"] is None


async def test_the_same_cookie_now_resolves_to_the_target(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    session = await app_client.get("/auth/session")
    assert session.status_code == 200
    body = session.json()
    assert body["id"] == trainer.id
    assert body["role"] == "trainer"
    assert body["impersonation"] is not None
    assert body["impersonation"]["target"]["user_id"] == trainer.id
    assert body["impersonation"]["admin"]["role"] == "super_admin"


async def test_a_second_start_from_another_session_supersedes_the_first(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """FR-048. Starting a second impersonation *while impersonating* is
    unreachable on the same session — the effective user has already
    stopped being a Super Admin (research.md R2-15) — so this is
    necessarily a second `sessions` row for the same admin (e.g. a second
    browser). `get_open_for_admin` finds the first impersonation
    regardless of which session started it."""
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token_a = await create_session_cookie(db_session, admin)
    token_b = await create_session_cookie(db_session, admin)
    first_target = await create_user(db_session, role=UserRole.TRAINER)
    second_target = await create_user(db_session, role=UserRole.COACH)
    await db_session.commit()

    app_client.cookies.set("pp_session", token_a)
    first = await app_client.post("/admin/impersonations", json={"user_id": first_target.id})
    assert first.status_code == 201

    app_client.cookies.set("pp_session", token_b)
    second = await app_client.post("/admin/impersonations", json={"user_id": second_target.id})
    assert second.status_code == 201

    session_b = await app_client.get("/auth/session")
    body_b = session_b.json()
    assert body_b["id"] == second_target.id
    assert body_b["impersonation"]["target"]["user_id"] == second_target.id

    # The superseded session's pointer was cleared — it resolves back to
    # the admin's own identity rather than a dangling impersonation.
    app_client.cookies.set("pp_session", token_a)
    session_a = await app_client.get("/auth/session")
    body_a = session_a.json()
    assert body_a["id"] == admin.id
    assert body_a["impersonation"] is None
