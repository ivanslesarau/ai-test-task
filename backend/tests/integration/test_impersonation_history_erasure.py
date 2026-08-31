"""US7 (tasks.md T647): a history entry survives the erasure of the
impersonated account, still naming it by identifier and rendering the
anonymized display name erasure leaves behind (FR-055, SC-017).
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def _sign_in_admin(app_client: AsyncClient, db_session: AsyncSession) -> object:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return admin


async def test_the_history_entry_survives_erasure_of_the_impersonated_account(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201
    ended = await app_client.delete("/admin/impersonations/current")
    assert ended.status_code == 204

    erased = await app_client.post(
        f"/admin/users/{trainer.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )
    assert erased.status_code == 200

    history = await app_client.get("/admin/impersonations")

    assert history.status_code == 200
    body = history.json()
    row = next(item for item in body["items"] if item["target"]["user_id"] == trainer.id)
    assert row["admin"]["user_id"] == admin.id  # type: ignore[attr-defined]
    assert row["target"]["display_name"] not in ("", None)
    assert row["ended_at"] is not None


async def test_an_impersonation_open_when_the_target_is_erased_ends_as_target_erased(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    # A second Super Admin performs the erasure — the acting admin's own
    # session is left mid-impersonation, exactly as FR-050 and the
    # lifecycle hook (data-model.md §114) describe.
    other_admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    other_token = await create_session_cookie(db_session, other_admin)
    await db_session.commit()

    other_client_cookies = app_client.cookies
    admin_token = other_client_cookies.get("pp_session")
    app_client.cookies.set("pp_session", other_token)
    erased = await app_client.post(
        f"/admin/users/{trainer.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )
    assert erased.status_code == 200

    app_client.cookies.set("pp_session", admin_token)
    session = await app_client.get("/auth/session")

    assert session.status_code == 200
    body = session.json()
    assert body["impersonation"] is None
    assert body["impersonation_ended"]["end_reason"] == "target_erased"
