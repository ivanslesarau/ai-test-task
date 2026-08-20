from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_token, hash_token
from app.db.base import new_uuid, utcnow
from app.models.auth import CredentialSetupInvitation
from app.models.enums import AccountStatus, UserRole
from tests.helpers import create_user


async def _create_invitation(
    db_session: AsyncSession,
    user_id: str,
    *,
    issued_by: str,
    expires_in_hours: int = 24,
    consumed: bool = False,
    superseded: bool = False,
) -> str:
    raw_token = generate_token()
    now = utcnow()
    db_session.add(
        CredentialSetupInvitation(
            id=new_uuid(),
            user_id=user_id,
            token_hash=hash_token(raw_token),
            issued_by_user_id=issued_by,
            created_at=now,
            expires_at=now + timedelta(hours=expires_in_hours),
            consumed_at=now if consumed else None,
            superseded_at=now if superseded else None,
        )
    )
    await db_session.flush()
    return raw_token


async def test_check_and_consume_a_usable_invitation(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    invited = await create_user(db_session, role=UserRole.TRAINER, with_password=False)
    token = await _create_invitation(db_session, invited.id, issued_by=admin.id)
    await db_session.commit()

    check = await app_client.get(f"/auth/setup-password/{token}")
    assert check.status_code == 200
    assert check.json()["email_hint"].endswith(invited.email.split("@")[1])

    setup = await app_client.post(
        "/auth/setup-password", json={"token": token, "password": "a-brand-new-password-99"}
    )
    assert setup.status_code == 204

    sign_in = await app_client.post(
        "/auth/login", json={"email": invited.email, "password": "a-brand-new-password-99"}
    )
    assert sign_in.status_code == 200


async def test_reusing_a_consumed_link_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    invited = await create_user(db_session, role=UserRole.COACH, with_password=False)
    token = await _create_invitation(db_session, invited.id, issued_by=admin.id, consumed=True)
    await db_session.commit()

    response = await app_client.post(
        "/auth/setup-password", json={"token": token, "password": "some-password-123456"}
    )
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "invitation_not_usable"


async def test_expired_link_is_refused(app_client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    invited = await create_user(db_session, role=UserRole.COACH, with_password=False)
    token = await _create_invitation(
        db_session, invited.id, issued_by=admin.id, expires_in_hours=-1
    )
    await db_session.commit()

    response = await app_client.get(f"/auth/setup-password/{token}")
    assert response.status_code == 410


async def test_superseded_link_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    invited = await create_user(db_session, role=UserRole.COACH, with_password=False)
    token = await _create_invitation(db_session, invited.id, issued_by=admin.id, superseded=True)
    await db_session.commit()

    response = await app_client.get(f"/auth/setup-password/{token}")
    assert response.status_code == 410


async def test_link_for_a_deactivated_account_before_setup_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    invited = await create_user(
        db_session, role=UserRole.COACH, status=AccountStatus.INACTIVE, with_password=False
    )
    token = await _create_invitation(db_session, invited.id, issued_by=admin.id)
    await db_session.commit()

    response = await app_client.get(f"/auth/setup-password/{token}")
    assert response.status_code == 410


async def test_password_rejected_by_policy_leaves_invitation_usable(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    invited = await create_user(db_session, role=UserRole.COACH, with_password=False)
    token = await _create_invitation(db_session, invited.id, issued_by=admin.id)
    await db_session.commit()

    response = await app_client.post(
        "/auth/setup-password", json={"token": token, "password": "short"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["fields"][0]["field"] == "password"
