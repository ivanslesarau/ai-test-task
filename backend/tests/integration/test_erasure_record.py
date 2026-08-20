from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_erasure_record_has_full_contents_for_a_super_admin(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    coach = await create_user(
        db_session,
        role=UserRole.COACH,
        email="original@example.org",
        first_name="Original",
        last_name="Name",
    )
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    await app_client.post(
        f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )

    response = await app_client.get(f"/admin/erasure-records/{coach.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["original_email"] == "original@example.org"
    assert body["original_first_name"] == "Original"
    assert body["original_last_name"] == "Name"
    assert body["reason"] == "GDPR request"
    assert body["erased_by"]["id"] == admin.id


async def test_erasure_record_is_forbidden_for_a_trainer(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    coach = await create_user(db_session, role=UserRole.COACH)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    trainer_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()

    app_client.cookies.set("pp_session", admin_token)
    await app_client.post(f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "x"})

    app_client.cookies.set("pp_session", trainer_token)
    response = await app_client.get(f"/admin/erasure-records/{coach.id}")

    assert response.status_code == 403


async def test_erasure_record_is_absent_from_ordinary_account_views(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    coach = await create_user(db_session, role=UserRole.COACH, email="hidden@example.org")
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    await app_client.post(f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "x"})

    detail = await app_client.get(f"/admin/users/{coach.id}")

    assert "hidden@example.org" not in detail.text
    assert "original" not in detail.text.lower()
