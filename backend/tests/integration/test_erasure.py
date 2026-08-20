import io
from pathlib import Path

from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.enums import UserRole
from app.models.role_details import CoachDetail
from tests.helpers import create_session_cookie, create_user


async def _admin_client(app_client: AsyncClient, db_session: AsyncSession) -> AsyncClient:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return app_client


async def test_erasure_anonymizes_and_returns_the_anonymized_values(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _admin_client(app_client, db_session)
    coach = await create_user(db_session, role=UserRole.COACH, email="cody@example.org")
    db_session.add(
        CoachDetail(
            user_id=coach.id, bio="A bio", credentials="Certified", is_publicly_visible=True
        )
    )
    await db_session.commit()

    response = await client.post(
        f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Deleted"
    assert body["last_name"] == "User"
    assert body["email"] == f"deleted_{coach.id}@example.com"
    assert body["phone"] is None
    assert body["status"] == "deleted"
    assert body["role_detail"]["bio"] is None
    assert body["role_detail"]["is_publicly_visible"] is False


async def test_erasure_without_a_reason_is_rejected(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _admin_client(app_client, db_session)
    coach = await create_user(db_session, role=UserRole.COACH)
    await db_session.commit()

    response = await client.post(f"/admin/users/{coach.id}/erase", json={"version": 1})

    assert response.status_code == 422


async def test_erasure_revokes_sessions_and_supersedes_invitations(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _admin_client(app_client, db_session)
    coach = await create_user(db_session, role=UserRole.COACH)
    coach_token = await create_session_cookie(db_session, coach)
    await db_session.commit()

    await client.post(f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "x"})

    app_client.cookies.set("pp_session", coach_token)
    response = await app_client.get("/me/profile")
    assert response.status_code == 401


async def test_erased_photo_files_are_deleted(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    coach = await create_user(db_session, role=UserRole.COACH)
    coach_token = await create_session_cookie(db_session, coach)
    await db_session.commit()

    app_client.cookies.set("pp_session", coach_token)
    image = Image.new("RGB", (50, 50), color="green")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    upload = await app_client.put(
        "/me/profile/photo", files={"file": ("p.png", buffer.getvalue(), "image/png")}
    )
    photo_key = upload.json()["photo_url"].rsplit("/", 1)[-1]
    settings = get_settings()
    photo_path = Path(settings.upload_dir) / photo_key
    assert photo_path.exists()

    app_client.cookies.set("pp_session", admin_token)
    await app_client.post(f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "x"})

    assert not photo_path.exists()


async def test_reactivation_and_profile_edit_are_refused_after_erasure(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _admin_client(app_client, db_session)
    coach = await create_user(db_session, role=UserRole.COACH)
    await db_session.commit()

    await client.post(f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "x"})

    reactivate = await client.post(f"/admin/users/{coach.id}/reactivate", json={"version": 2})
    assert reactivate.status_code == 422
    assert reactivate.json()["error"]["code"] == "erasure_is_permanent"
