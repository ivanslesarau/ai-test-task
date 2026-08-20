from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_token, hash_password, hash_token
from app.db.base import new_uuid, utcnow
from app.models.auth import Session as SessionModel
from app.models.enums import AccountStatus, UserRole
from app.models.user import User, UserProfile

KNOWN_PASSWORD = "correct-horse-battery-987654"


async def create_user(
    db_session: AsyncSession,
    *,
    role: UserRole,
    status: AccountStatus = AccountStatus.ACTIVE,
    email: str | None = None,
    with_password: bool = True,
    first_name: str = "Test",
    last_name: str = "User",
) -> User:
    now = utcnow()
    user = User(
        id=new_uuid(),
        email=(email or f"{role.value}-{new_uuid()}@example.org").lower(),
        password_hash=hash_password(KNOWN_PASSWORD) if with_password else None,
        role=role.value,
        status=status.value,
        version=1,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UserProfile(user_id=user.id, first_name=first_name, last_name=last_name, updated_at=now)
    )
    await db_session.flush()
    return user


async def create_session_cookie(db_session: AsyncSession, user: User, *, idle_days: int = 7) -> str:
    """Bypasses the login endpoint for test speed — issues a session
    directly, exactly as AuthService.sign_in would."""
    raw_token = generate_token()
    now = utcnow()
    db_session.add(
        SessionModel(
            id=new_uuid(),
            user_id=user.id,
            token_hash=hash_token(raw_token),
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=idle_days),
        )
    )
    await db_session.flush()
    return raw_token
