from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_share_link_code, generate_token, hash_password, hash_token
from app.db.base import new_uuid, utcnow
from app.models.approval import APPROVAL_REQUEST_TTL_HOURS, ApprovalRequest
from app.models.association import TrainerPlayerAssociation
from app.models.auth import Session as SessionModel
from app.models.coach_invitation import CoachInvitation
from app.models.enums import (
    AccountStatus,
    ApprovalRequestKind,
    ApprovalRequestStatus,
    AssociationStatus,
    CoachInvitationState,
    Gender,
    PlayerProfileKind,
    ShareLinkKind,
    UserRole,
)
from app.models.player_profile import PlayerProfile
from app.models.role_details import CoachDetail, ParentContact, TrainerOrganization
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


async def create_player_profile(
    db_session: AsyncSession,
    *,
    account: User,
    kind: str = "self",
    first_name: str | None = None,
    last_name: str | None = None,
    date_of_birth: date | None = None,
    gender: str = Gender.PREFER_NOT_TO_SAY.value,
    school: str | None = None,
    jersey_number: str | None = None,
    skill_level: str | None = None,
    tokens_without_approval: bool = False,
    sign_in_user_id: str | None = None,
    photo_key: str | None = None,
) -> PlayerProfile:
    """One `player_profiles` row on `account` (data-model.md §26,
    extension 2026-08-27). Replaces `create_player_with_detail`, which
    created one `PlayerDetail` per account and is the single biggest
    source of breakage this phase fixes (tasks.md T340) — `account` is
    now an argument rather than created here, because a family account
    may hold several profiles.

    `kind='self'` forces `first_name`/`last_name` to `NULL`
    (`ck_player_profiles_self_names`, research.md R-37) regardless of
    what is passed; a `'child'` defaults to a distinct name so two
    children on the same account do not collide by accident."""
    if kind == PlayerProfileKind.SELF.value:
        first_name, last_name = None, None
        if date_of_birth is None:
            date_of_birth = date.today() - timedelta(days=366 * 25)
    else:
        first_name = first_name or "Child"
        last_name = last_name or "Test"
        if date_of_birth is None:
            date_of_birth = date.today() - timedelta(days=366 * 10)

    now = utcnow()
    profile = PlayerProfile(
        id=new_uuid(),
        account_user_id=account.id,
        kind=kind,
        first_name=first_name,
        last_name=last_name,
        photo_key=photo_key,
        date_of_birth=date_of_birth,
        gender=gender,
        school=school,
        jersey_number=jersey_number,
        skill_level=skill_level,
        tokens_without_approval=tokens_without_approval,
        sign_in_user_id=sign_in_user_id,
        removed_at=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(profile)
    await db_session.flush()
    return profile


async def create_family(
    db_session: AsyncSession, *, children: int = 2, with_sign_in: bool = False
) -> tuple[User, list[PlayerProfile], list[User]]:
    """A parent account, its `ParentContact`, and `children` CHILD
    profiles (extension 2026-08-27, tasks.md T340). When `with_sign_in`
    is true, each child also gets its own signed-in account and
    `player_profiles.sign_in_user_id` names it (FR-129) — the fixture
    Phase C's sibling-isolation tests need. Returns
    `(parent, profiles, child_accounts)`; `child_accounts` is empty
    unless `with_sign_in` is set."""
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    db_session.add(ParentContact(user_id=parent.id))
    await db_session.flush()

    profiles: list[PlayerProfile] = []
    child_accounts: list[User] = []
    for i in range(children):
        sign_in_user: User | None = None
        if with_sign_in:
            sign_in_user = await create_user(
                db_session,
                role=UserRole.PLAYER_PARENT,
                email=f"child-{i}-{new_uuid()}@example.org",
                first_name=f"Child{i}",
            )
            child_accounts.append(sign_in_user)

        profile = await create_player_profile(
            db_session,
            account=parent,
            kind=PlayerProfileKind.CHILD.value,
            first_name=f"Child{i}",
            last_name="Family",
            sign_in_user_id=sign_in_user.id if sign_in_user is not None else None,
        )
        profiles.append(profile)

    return parent, profiles, child_accounts


async def create_association(
    db_session: AsyncSession,
    *,
    trainer_id: str,
    player_profile_id: str,
    share_link_id: str | None = None,
    status: str = AssociationStatus.ACTIVE.value,
) -> TrainerPlayerAssociation:
    """A `trainer_player_associations` row at profile granularity
    (data-model.md §29.1). Centralizes what used to be a `_associate`
    helper hand-rolled in every context/roster/isolation test file — each
    one wrote `player_user_id` directly, which no longer exists."""
    now = utcnow()
    association = TrainerPlayerAssociation(
        id=new_uuid(),
        trainer_user_id=trainer_id,
        player_profile_id=player_profile_id,
        share_link_id=share_link_id,
        status=status,
        joined_at=now,
        updated_at=now,
    )
    db_session.add(association)
    await db_session.flush()
    return association


async def create_approval_request(
    db_session: AsyncSession,
    *,
    player_profile_id: str,
    parent_user_id: str,
    kind: ApprovalRequestKind = ApprovalRequestKind.JOIN_TRAINER,
    trainer_user_id: str | None = None,
    share_link_id: str | None = None,
    amount_minor: int | None = None,
    currency: str | None = None,
    status: ApprovalRequestStatus = ApprovalRequestStatus.PENDING_PARENT_APPROVAL,
    requested_at: datetime | None = None,
    expires_at: datetime | None = None,
    parent_note: str | None = None,
    child_note: str | None = None,
    resolved_at: datetime | None = None,
    resolved_by_user_id: str | None = None,
) -> ApprovalRequest:
    """A raw `approval_requests` row, bypassing `ApprovalRepository.insert`
    so a test can set `expires_at` directly — the "injected clock" tests
    (T403, T404) need a request already past its deadline without waiting
    48 hours (research.md R-43). `requested_at`/`expires_at` default to
    "just raised, expiring in 48 hours", matching `insert`'s own default."""
    now = utcnow()
    requested_at = requested_at or now
    if expires_at is None:
        expires_at = requested_at + timedelta(hours=APPROVAL_REQUEST_TTL_HOURS)
    request = ApprovalRequest(
        id=new_uuid(),
        player_profile_id=player_profile_id,
        parent_user_id=parent_user_id,
        kind=kind.value,
        status=status.value,
        trainer_user_id=trainer_user_id,
        share_link_id=share_link_id,
        amount_minor=amount_minor,
        currency=currency,
        requested_at=requested_at,
        expires_at=expires_at,
        parent_note=parent_note,
        child_note=child_note,
        resolved_at=resolved_at,
        resolved_by_user_id=resolved_by_user_id,
    )
    db_session.add(request)
    await db_session.flush()
    return request


async def create_coach_invitation(
    db_session: AsyncSession,
    *,
    trainer: User,
    invited_email: str = "prospect@example.org",
    invitee_name: str | None = None,
    message: str | None = None,
    expires_at: datetime | None = None,
    state: CoachInvitationState = CoachInvitationState.AWAITING,
) -> tuple[CoachInvitation, str]:
    """A `coach_invitations` row plus the raw token that hashes to
    `token_hash` (extension 2026-08-28, US2) — since only the hash is
    ever stored (research.md R2-02), a test that needs to call
    `GET/POST /coach-invitations/{token}...` must create the row this way
    rather than through the trainer-issuing endpoint, whose JSON response
    never carries the raw token either."""
    raw_token = generate_token()
    now = utcnow()
    invitation = CoachInvitation(
        id=new_uuid(),
        trainer_user_id=trainer.id,
        created_by_user_id=trainer.id,
        token_hash=hash_token(raw_token),
        invited_email=invited_email.lower(),
        invitee_name=invitee_name,
        message=message,
        state=state.value,
        issued_at=now,
        expires_at=expires_at or (now + timedelta(days=7)),
        accepted_by_user_id=None,
        accepted_at=None,
        revoked_at=None,
        superseded_at=None,
        superseded_by_id=None,
        blocked_at=None,
        blocked_reason=None,
    )
    db_session.add(invitation)
    await db_session.flush()
    return invitation, raw_token


async def create_coach(
    db_session: AsyncSession,
    *,
    email: str | None = None,
    status: AccountStatus = AccountStatus.ACTIVE,
    trainer_user_id: str | None = None,
    joined_at: datetime | None = None,
    first_name: str = "Cody",
    last_name: str = "Coach",
) -> User:
    """A Coach account with its `coach_details` row (extension
    2026-08-28, US2). `trainer_user_id`/`joined_at` pre-assign the coach
    to a roster when given — both `None` (the default) leaves the coach
    on no roster, exactly as a freshly-registered coach starts."""
    coach = await create_user(
        db_session,
        role=UserRole.COACH,
        status=status,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    db_session.add(
        CoachDetail(
            user_id=coach.id,
            is_publicly_visible=False,
            trainer_user_id=trainer_user_id,
            joined_at=joined_at,
        )
    )
    await db_session.flush()
    return coach
