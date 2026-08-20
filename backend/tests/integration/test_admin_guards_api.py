import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ActionNotPermitted
from app.models.enums import UserRole
from app.services.ports.email_sender import FilesystemEmailSender
from app.services.user_admin_service import UserAdminService
from tests.helpers import create_session_cookie, create_user


async def test_super_admin_cannot_deactivate_their_own_account(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/admin/users/{admin.id}/deactivate", json={"version": 1})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "self_action_forbidden"


async def test_deactivating_the_only_active_super_admin_is_refused(
    db_session: AsyncSession,
) -> None:
    """The last-active-admin guard, exercised directly at the service
    layer with a distinct actor.

    This cannot be reached through the HTTP API with two real, currently
    signed-in Super Admins: whoever is authenticated to call the endpoint
    is themselves an active Super Admin, so count_active_super_admins()
    is always >= 2 whenever actor != target — deactivating either one
    then legitimately leaves 1 remaining. The only way a *distinct* actor
    can face a target that is the sole active Super Admin is a concurrent
    request racing with another deactivation (research.md R-09), which
    this single-transaction test harness cannot simulate. Calling the
    service directly with an arbitrary actor isolates the guard's own
    logic from that reachability constraint, which is a router/session
    concern, not a business rule this test needs to re-prove.
    """
    only_admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    someone_else = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    settings = get_settings()
    service = UserAdminService(
        db_session, settings, FilesystemEmailSender(settings.email_outbox_dir)
    )

    with pytest.raises(ActionNotPermitted) as exc_info:
        await service.deactivate(only_admin.id, actor=someone_else, expected_version=1)

    assert exc_info.value.code == "last_super_admin"


async def test_deactivating_a_super_admin_succeeds_once_a_second_one_exists(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    second_admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, second_admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/admin/users/{admin.id}/deactivate", json={"version": 1})

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
