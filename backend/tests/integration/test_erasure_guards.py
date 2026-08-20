import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ActionNotPermitted
from app.models.enums import UserRole
from app.services.erasure_service import ErasureService
from app.services.ports.email_sender import FilesystemEmailSender
from app.services.ports.photo_storage import get_photo_storage
from app.services.user_admin_service import UserAdminService
from tests.helpers import create_session_cookie, create_user


async def test_super_admin_cannot_erase_their_own_account(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(
        f"/admin/users/{admin.id}/erase", json={"version": 1, "reason": "x"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "self_action_forbidden"


async def test_erasing_the_only_active_super_admin_is_refused(db_session: AsyncSession) -> None:
    """Same reachability constraint as the deactivate guard
    (test_admin_guards_api.py): a distinct, authenticated actor is
    necessarily itself an active Super Admin, so this path is exercised
    directly at the service layer — see that file's docstring for the
    full reasoning."""
    only_admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    someone_else = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    settings = get_settings()
    admin_service = UserAdminService(
        db_session, settings, FilesystemEmailSender(settings.email_outbox_dir)
    )
    erasure_service = ErasureService(
        db_session, get_photo_storage(settings.upload_dir), admin_service
    )

    with pytest.raises(ActionNotPermitted) as exc_info:
        await erasure_service.erase(
            only_admin.id, actor=someone_else, expected_version=1, reason="x"
        )

    assert exc_info.value.code == "last_super_admin"
