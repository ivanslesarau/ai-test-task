"""US6 (tasks.md T620, FR-050, data-model.md §114): the five lifecycle
hooks — sign-out, target deactivation when it started Active, an
Inactive-at-start target staying Inactive (does NOT end), erasure, and
the admin's own deactivation.
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus, UserRole
from app.models.impersonation import ImpersonationSession
from tests.helpers import create_session_cookie, create_user


async def test_signing_out_closes_the_open_impersonation_as_signed_out(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    app_client.cookies.set("pp_session", admin_token)
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    logout = await app_client.post("/auth/logout")
    assert logout.status_code == 204

    result = await db_session.execute(
        select(ImpersonationSession).where(ImpersonationSession.admin_user_id == admin.id)
    )
    record = result.scalar_one()
    assert record.ended_at is not None
    assert record.end_reason == "signed_out"


async def test_deactivating_a_target_that_started_active_ends_the_impersonation(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    second_admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    second_admin_token = await create_session_cookie(db_session, second_admin)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    app_client.cookies.set("pp_session", admin_token)
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    app_client.cookies.set("pp_session", second_admin_token)
    deactivated = await app_client.post(
        f"/admin/users/{trainer.id}/deactivate", json={"version": trainer.version}
    )
    assert deactivated.status_code == 200

    app_client.cookies.set("pp_session", admin_token)
    session = await app_client.get("/auth/session")
    body = session.json()
    assert body["id"] == admin.id
    assert body["impersonation"] is None
    assert body["impersonation_ended"]["end_reason"] == "target_deactivated"


async def test_a_target_inactive_at_start_staying_inactive_does_not_end(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    trainer = await create_user(db_session, role=UserRole.TRAINER, status=AccountStatus.INACTIVE)
    await db_session.commit()

    app_client.cookies.set("pp_session", admin_token)
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201
    assert started.json()["target_status_at_start"] == "inactive"

    session = await app_client.get("/auth/session")
    body = session.json()
    assert body["id"] == trainer.id
    assert body["impersonation"] is not None


async def test_erasing_the_target_ends_the_impersonation_as_target_erased(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    second_admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    second_admin_token = await create_session_cookie(db_session, second_admin)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    app_client.cookies.set("pp_session", admin_token)
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    app_client.cookies.set("pp_session", second_admin_token)
    erased = await app_client.post(
        f"/admin/users/{trainer.id}/erase",
        json={"version": trainer.version, "reason": "test erasure"},
    )
    assert erased.status_code == 200

    app_client.cookies.set("pp_session", admin_token)
    session = await app_client.get("/auth/session")
    body = session.json()
    assert body["id"] == admin.id
    assert body["impersonation"] is None
    assert body["impersonation_ended"]["end_reason"] == "target_erased"


async def test_deactivating_the_admin_ends_their_own_open_impersonation(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    second_admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    second_admin_token = await create_session_cookie(db_session, second_admin)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    app_client.cookies.set("pp_session", admin_token)
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    app_client.cookies.set("pp_session", second_admin_token)
    deactivated = await app_client.post(
        f"/admin/users/{admin.id}/deactivate", json={"version": admin.version}
    )
    assert deactivated.status_code == 200

    # The admin's own account is now Inactive, so their session no longer
    # authenticates at all (FR-018) — the impersonation's own closure is
    # verified directly against the append-only history instead.
    result = await db_session.execute(
        select(ImpersonationSession).where(ImpersonationSession.admin_user_id == admin.id)
    )
    record = result.scalar_one()
    assert record.ended_at is not None
    assert record.end_reason == "admin_deactivated"
