"""FR-056/SC-012: no client-visible response, under any failure
condition, may contain a stack trace, driver message, or credential
material."""

from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user

_FORBIDDEN_SUBSTRINGS = [
    "Traceback",
    "sqlite3",
    "sqlalchemy",
    "IntegrityError",
    "password_hash",
    '.py", line',
]


def _assert_body_is_clean(text: str) -> None:
    lowered = text.lower()
    for marker in _FORBIDDEN_SUBSTRINGS:
        assert marker.lower() not in lowered, f"response leaked internal detail: {marker!r}"


async def test_an_unexpected_database_failure_returns_a_generic_body(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Uses a dedicated client with `raise_app_exceptions=False`: Starlette
    sends the 500 response and then re-raises the original exception for
    server-side observability (by design — it's what a real deployment's
    logs capture). httpx's default ASGITransport surfaces that re-raise as
    a Python exception in the test itself rather than the response it was
    sent alongside, which would make this test fail even though a real
    client talking to a real uvicorn process receives exactly the clean
    body asserted below (verified manually against a live server)."""
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    from app.main import app as fastapi_app

    non_raising_client = AsyncClient(
        transport=ASGITransport(app=fastapi_app, raise_app_exceptions=False),
        base_url="http://test/api/v1",
        cookies=app_client.cookies,
    )

    with patch(
        "app.repositories.user_repository.UserRepository.list_directory",
        new_callable=AsyncMock,
        side_effect=RuntimeError("simulated: connection to sqlite3 backend lost, password=secret"),
    ):
        response = await non_raising_client.get("/admin/users")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    _assert_body_is_clean(response.text)
    assert "secret" not in response.text


async def test_a_domain_error_response_carries_no_stack_trace(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/admin/users/does-not-exist")

    assert response.status_code == 404
    _assert_body_is_clean(response.text)


async def test_validation_error_response_carries_no_internal_detail(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(
        "/admin/users",
        json={
            "role": "not-a-role",
            "email": "x@x.com",
            "first_name": "A",
            "last_name": "B",
            "phone": "1",
        },
    )

    assert response.status_code == 422
    _assert_body_is_clean(response.text)
