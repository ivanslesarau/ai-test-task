import io

from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import create_session_cookie, create_trainer_with_link

_CLEAN_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    b'<circle cx="5" cy="5" r="4"/></svg>'
)


def _png_bytes() -> bytes:
    image = Image.new("RGB", (50, 50), color="green")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def test_branding_media_is_served_without_a_session(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    upload = await app_client.put(
        "/me/branding/logo", files={"file": ("logo.png", _png_bytes(), "image/png")}
    )
    logo_url = upload.json()["logo_url"]

    app_client.cookies.delete("pp_session")
    response = await app_client.get(logo_url)

    assert response.status_code == 200


async def test_svg_response_carries_nosniff_and_a_locked_down_csp(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    upload = await app_client.put(
        "/me/branding/logo", files={"file": ("logo.svg", _CLEAN_SVG, "image/svg+xml")}
    )
    logo_url = upload.json()["logo_url"]

    app_client.cookies.delete("pp_session")
    response = await app_client.get(logo_url)

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["content-type"] == "image/svg+xml"


async def test_png_response_does_not_carry_the_svg_csp(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    upload = await app_client.put(
        "/me/branding/logo", files={"file": ("logo.png", _png_bytes(), "image/png")}
    )
    logo_url = upload.json()["logo_url"]

    response = await app_client.get(logo_url)

    assert response.status_code == 200
    assert "content-security-policy" not in response.headers


async def test_unknown_key_is_404(app_client: AsyncClient) -> None:
    response = await app_client.get("/media/branding/not-a-real-key.png")
    assert response.status_code == 404
