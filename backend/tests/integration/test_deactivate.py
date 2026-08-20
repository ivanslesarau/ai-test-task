from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus, UserRole
from tests.helpers import KNOWN_PASSWORD, create_session_cookie, create_user


async def _admin_client(app_client: AsyncClient, db_session: AsyncSession) -> AsyncClient:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return app_client


async def test_deactivate_then_sign_in_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _admin_client(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    response = await client.post(f"/admin/users/{trainer.id}/deactivate", json={"version": 1})

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"

    sign_in = await client.post(
        "/auth/login", json={"email": trainer.email, "password": KNOWN_PASSWORD}
    )
    assert sign_in.status_code == 403
    assert sign_in.json()["error"]["code"] == "account_not_active"


async def test_reactivate_restores_access_with_existing_password(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _admin_client(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER, status=AccountStatus.INACTIVE)
    await db_session.commit()

    response = await client.post(f"/admin/users/{trainer.id}/reactivate", json={"version": 1})

    assert response.status_code == 200
    assert response.json()["status"] == "active"

    sign_in = await client.post(
        "/auth/login", json={"email": trainer.email, "password": KNOWN_PASSWORD}
    )
    assert sign_in.status_code == 200


async def test_deactivating_an_already_inactive_account_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _admin_client(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER, status=AccountStatus.INACTIVE)
    await db_session.commit()

    response = await client.post(f"/admin/users/{trainer.id}/deactivate", json={"version": 1})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_status_transition"


async def test_reactivating_a_deleted_account_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _admin_client(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER, status=AccountStatus.DELETED)
    await db_session.commit()

    response = await client.post(f"/admin/users/{trainer.id}/reactivate", json={"version": 1})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "erasure_is_permanent"
