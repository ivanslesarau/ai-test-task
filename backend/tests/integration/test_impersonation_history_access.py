"""US7 (tasks.md T645): the impersonation history is Super-Admin-only,
refused on the request rather than by a hidden control (FR-056).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def _sign_in(app_client: AsyncClient, db_session: AsyncSession, role: UserRole) -> None:
    user = await create_user(db_session, role=role)
    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


@pytest.mark.parametrize("role", [UserRole.TRAINER, UserRole.COACH, UserRole.PLAYER_PARENT])
async def test_a_non_super_admin_is_refused_the_history(
    app_client: AsyncClient, db_session: AsyncSession, role: UserRole
) -> None:
    await _sign_in(app_client, db_session, role)

    response = await app_client.get("/admin/impersonations")

    assert response.status_code == 403


async def test_an_unauthenticated_caller_is_401(app_client: AsyncClient) -> None:
    response = await app_client.get("/admin/impersonations")
    assert response.status_code == 401
