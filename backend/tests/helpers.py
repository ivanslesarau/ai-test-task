from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_share_link_code, generate_token, hash_password, hash_token
from app.db.base import new_uuid, utcnow
from app.models.auth import Session as SessionModel
from app.models.enums import AccountStatus, ShareLinkKind, UserRole
from app.models.role_details import ParentContact, PlayerDetail, TrainerOrganization
from app.models.share_link import ShareLink
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


async def create_trainer_with_link(
    db_session: AsyncSession,
    *,
    business_name: str = "Elite Basketball Academy",
    status: AccountStatus = AccountStatus.ACTIVE,
) -> tuple[User, ShareLink]:
    """A Trainer with its organization row and a fresh standing player
    ShareLink — the fixture every US6/US7/US8 test needs to reach a join
    page (extension 2026-08-26)."""
    trainer = await create_user(db_session, role=UserRole.TRAINER, status=status)
    db_session.add(TrainerOrganization(user_id=trainer.id, business_name=business_name))
    link = ShareLink(
        id=new_uuid(),
        code=generate_share_link_code(),
        trainer_user_id=trainer.id,
        created_by_user_id=trainer.id,
        kind=ShareLinkKind.PLAYER_STANDING.value,
        target_email=None,
        expires_at=None,
        max_uses=None,
        use_count=0,
        is_active=True,
        revoked_at=None,
        created_at=utcnow(),
    )
    db_session.add(link)
    await db_session.flush()
    return trainer, link


async def create_player_with_detail(
    db_session: AsyncSession, *, is_self: bool = True, **user_kwargs: object
) -> User:
    """A Player/Parent with its PlayerDetail and ParentContact rows —
    what `create_user` alone omits, and what TrainerContextService
    requires to resolve a context at all (extension 2026-08-26)."""
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT, **user_kwargs)
    db_session.add(PlayerDetail(user_id=player.id, is_self=is_self))
    db_session.add(ParentContact(user_id=player.id))
    await db_session.flush()
    return player
