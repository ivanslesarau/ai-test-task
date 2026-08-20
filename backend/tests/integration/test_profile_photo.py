import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


def _png_bytes(size: tuple[int, int] = (200, 200)) -> bytes:
    image = Image.new("RGB", size, color="red")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
async def coach_client(app_client: AsyncClient, db_session: AsyncSession) -> AsyncClient:
    user = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return app_client


async def test_upload_succeeds_and_photo_is_fetchable(coach_client: AsyncClient) -> None:
    response = await coach_client.put(
        "/me/profile/photo", files={"file": ("photo.png", _png_bytes(), "image/png")}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["photo_url"] and body["thumbnail_url"]

    original = await coach_client.get(body["photo_url"])
    assert original.status_code == 200
    thumb = await coach_client.get(body["thumbnail_url"])
    assert thumb.status_code == 200


async def test_oversized_upload_is_rejected_and_previous_photo_unchanged(
    coach_client: AsyncClient,
) -> None:
    first = await coach_client.put(
        "/me/profile/photo", files={"file": ("photo.png", _png_bytes(), "image/png")}
    )
    original_url = first.json()["photo_url"]

    settings = get_settings()
    oversized = b"\x00" * (settings.max_upload_bytes + 1)
    response = await coach_client.put(
        "/me/profile/photo", files={"file": ("big.png", oversized, "image/png")}
    )

    assert response.status_code == 413

    profile = await coach_client.get("/me/profile")
    assert profile.json()["photo_url"] == original_url


async def test_renamed_non_image_file_is_rejected(coach_client: AsyncClient) -> None:
    response = await coach_client.put(
        "/me/profile/photo",
        files={"file": ("photo.jpg", b"this is definitely not an image", "image/jpeg")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_image"


async def test_replacing_a_photo_deletes_the_previous_files(
    coach_client: AsyncClient,
) -> None:
    settings = get_settings()
    first = await coach_client.put(
        "/me/profile/photo", files={"file": ("photo.png", _png_bytes(), "image/png")}
    )
    first_key = first.json()["photo_url"].rsplit("/", 1)[-1]
    first_path = Path(settings.upload_dir) / first_key
    assert first_path.exists()

    await coach_client.put(
        "/me/profile/photo", files={"file": ("photo2.png", _png_bytes((50, 50)), "image/png")}
    )

    assert not first_path.exists()
