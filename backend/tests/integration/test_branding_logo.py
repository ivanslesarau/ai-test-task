import io

from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_trainer_with_link, create_user

_TWO_MB = 2 * 1024 * 1024


def _png_bytes(size: tuple[int, int] = (100, 100)) -> bytes:
    image = Image.new("RGB", size, color="blue")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


_CLEAN_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    b'<circle cx="5" cy="5" r="4"/></svg>'
)

_HOSTILE_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


async def _sign_in_trainer(app_client: AsyncClient, db_session: AsyncSession):
    trainer, _ = await create_trainer_with_link(db_session)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return trainer


async def test_accepted_png_upload_succeeds(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(app_client, db_session)

    response = await app_client.put(
        "/me/branding/logo", files={"file": ("logo.png", _png_bytes(), "image/png")}
    )

    assert response.status_code == 200
    assert response.json()["logo_url"] is not None


async def test_oversized_file_is_refused_with_413(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(app_client, db_session)
    first = await app_client.put(
        "/me/branding/logo", files={"file": ("logo.png", _png_bytes(), "image/png")}
    )
    original_url = first.json()["logo_url"]

    oversized = b"\x00" * (_TWO_MB + 1)
    response = await app_client.put(
        "/me/branding/logo", files={"file": ("big.png", oversized, "image/png")}
    )

    assert response.status_code == 413
    unchanged = await app_client.get("/me/branding")
    assert unchanged.json()["logo_url"] == original_url


async def test_mislabelled_file_is_rejected(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(app_client, db_session)

    response = await app_client.put(
        "/me/branding/logo", files={"file": ("logo.png", b"not-a-real-image-at-all", "image/png")}
    )

    assert response.status_code == 422


async def test_oversized_dimensions_are_fitted_not_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(app_client, db_session)

    response = await app_client.put(
        "/me/branding/logo",
        files={"file": ("logo.png", _png_bytes((1200, 1200)), "image/png")},
    )

    assert response.status_code == 200
    logo_url = response.json()["logo_url"]
    fetched = await app_client.get(logo_url)
    assert fetched.status_code == 200
    image = Image.open(io.BytesIO(fetched.content))
    assert image.width <= 200
    assert image.height <= 200


async def test_a_hostile_svg_is_refused(app_client: AsyncClient, db_session: AsyncSession) -> None:
    await _sign_in_trainer(app_client, db_session)

    response = await app_client.put(
        "/me/branding/logo", files={"file": ("logo.svg", _HOSTILE_SVG, "image/svg+xml")}
    )

    assert response.status_code == 422


async def test_a_clean_svg_is_accepted_and_not_resized(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(app_client, db_session)

    response = await app_client.put(
        "/me/branding/logo", files={"file": ("logo.svg", _CLEAN_SVG, "image/svg+xml")}
    )

    assert response.status_code == 200
    logo_url = response.json()["logo_url"]
    fetched = await app_client.get(logo_url)
    assert fetched.status_code == 200
    assert fetched.content == _CLEAN_SVG


async def test_replacing_a_logo_removes_the_previous_file(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(app_client, db_session)
    first = await app_client.put(
        "/me/branding/logo", files={"file": ("logo.png", _png_bytes(), "image/png")}
    )
    first_url = first.json()["logo_url"]

    await app_client.put(
        "/me/branding/logo", files={"file": ("logo2.png", _png_bytes((50, 50)), "image/png")}
    )

    old = await app_client.get(first_url)
    assert old.status_code == 404


async def test_coach_and_player_are_refused_on_both_logo_endpoints(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Permission-matrix coverage for the two multipart logo endpoints,
    documented as excluded from test_permission_matrix.py's table."""
    coach = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    upload = await app_client.put(
        "/me/branding/logo", files={"file": ("logo.png", _png_bytes(), "image/png")}
    )
    delete = await app_client.delete("/me/branding/logo")

    assert upload.status_code == 403
    assert delete.status_code == 403
