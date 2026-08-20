from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus, UserRole
from tests.helpers import KNOWN_PASSWORD, create_session_cookie, create_user


async def test_login_success_admits_and_sets_session_cookie(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    response = await app_client.post(
        "/auth/login", json={"email": user.email, "password": KNOWN_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == user.email
    assert body["role"] == "trainer"

    set_cookie = response.headers.get("set-cookie", "")
    assert "pp_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "samesite=lax" in set_cookie.lower()


async def test_wrong_password_and_unknown_email_return_identical_401_body(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    wrong_password_response = await app_client.post(
        "/auth/login", json={"email": user.email, "password": "definitely-wrong-password"}
    )
    unknown_email_response = await app_client.post(
        "/auth/login",
        json={"email": "nobody-registered@example.org", "password": "whatever-password-123"},
    )

    assert wrong_password_response.status_code == 401
    assert unknown_email_response.status_code == 401
    assert wrong_password_response.json() == unknown_email_response.json()


async def test_correct_password_against_inactive_account_is_refused_distinctly(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session, role=UserRole.TRAINER, status=AccountStatus.INACTIVE)
    await db_session.commit()

    response = await app_client.post(
        "/auth/login", json={"email": user.email, "password": KNOWN_PASSWORD}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "account_not_active"


async def test_session_endpoint_requires_authentication(app_client: AsyncClient) -> None:
    response = await app_client.get("/auth/session")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_session_endpoint_returns_current_user_when_authenticated(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/auth/session")

    assert response.status_code == 200
    assert response.json()["id"] == user.id


async def test_sign_out_revokes_the_session_so_it_cannot_be_reused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    logout_response = await app_client.post("/auth/logout")
    assert logout_response.status_code == 204

    app_client.cookies.set("pp_session", token)
    reuse_response = await app_client.get("/auth/session")
    assert reuse_response.status_code == 401
