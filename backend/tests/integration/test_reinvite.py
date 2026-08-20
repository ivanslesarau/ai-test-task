from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import CredentialSetupInvitation
from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_reinvite_supersedes_the_outstanding_link(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    invited = await create_user(db_session, role=UserRole.TRAINER, with_password=False)
    await db_session.commit()
    app_client.cookies.set("pp_session", admin_token)

    response = await app_client.post(f"/admin/users/{invited.id}/reinvite")
    assert response.status_code == 200
    assert response.json()["invitation_sent"] is True

    rows = (
        (
            await db_session.execute(
                select(CredentialSetupInvitation).where(
                    CredentialSetupInvitation.user_id == invited.id
                )
            )
        )
        .scalars()
        .all()
    )
    usable = [r for r in rows if r.consumed_at is None and r.superseded_at is None]
    assert len(usable) == 1


async def test_reinvite_refused_once_a_password_is_set(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    invited = await create_user(db_session, role=UserRole.TRAINER, with_password=True)
    await db_session.commit()
    app_client.cookies.set("pp_session", admin_token)

    response = await app_client.post(f"/admin/users/{invited.id}/reinvite")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "already_has_password"
