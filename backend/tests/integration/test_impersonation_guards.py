"""US6 (tasks.md T616, FR-042, FR-047, research.md R2-15): every start
refusal is a single `422 impersonation_not_permitted`, an Inactive target
is permitted and labelled, and nested impersonation / deactivate / erase
are each refused explicitly while impersonating — structurally, with no
impersonation-specific code anywhere but the role gate itself.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus, UserRole
from tests.helpers import create_session_cookie, create_user


async def _sign_in_admin(app_client: AsyncClient, db_session: AsyncSession) -> str:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return admin.id


async def test_impersonating_another_super_admin_is_422(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    other_admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    await db_session.commit()

    response = await app_client.post("/admin/impersonations", json={"user_id": other_admin.id})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "impersonation_not_permitted"


async def test_impersonating_yourself_is_422(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin_id = await _sign_in_admin(app_client, db_session)

    response = await app_client.post("/admin/impersonations", json={"user_id": admin_id})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "impersonation_not_permitted"


async def test_impersonating_an_erased_account_is_422(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    erased = await create_user(db_session, role=UserRole.TRAINER, status=AccountStatus.DELETED)
    await db_session.commit()

    response = await app_client.post("/admin/impersonations", json={"user_id": erased.id})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "impersonation_not_permitted"


async def test_impersonating_an_inactive_account_succeeds_and_is_labelled(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    inactive = await create_user(db_session, role=UserRole.TRAINER, status=AccountStatus.INACTIVE)
    await db_session.commit()

    response = await app_client.post("/admin/impersonations", json={"user_id": inactive.id})

    assert response.status_code == 201
    assert response.json()["target_status_at_start"] == "inactive"


async def test_nested_impersonation_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    other = await create_user(db_session, role=UserRole.COACH)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    nested = await app_client.post("/admin/impersonations", json={"user_id": other.id})

    assert nested.status_code == 403


async def test_deactivating_anyone_is_refused_while_impersonating(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    some_other_user = await create_user(db_session, role=UserRole.COACH)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    response = await app_client.post(
        f"/admin/users/{some_other_user.id}/deactivate", json={"version": 1}
    )

    assert response.status_code == 403


async def test_erasing_anyone_is_refused_while_impersonating(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    some_other_user = await create_user(db_session, role=UserRole.COACH)
    await db_session.commit()

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    response = await app_client.post(
        f"/admin/users/{some_other_user.id}/erase",
        json={"version": 1, "reason": "test"},
    )

    assert response.status_code == 403
