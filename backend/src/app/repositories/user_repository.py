from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import StaleVersion
from app.db.base import new_uuid, utcnow
from app.models.enums import AccountStatus, UserRole
from app.models.role_details import CoachDetail, ParentContact, PlayerDetail, TrainerOrganization
from app.models.user import User, UserProfile

RoleDetailRow = TrainerOrganization | CoachDetail | tuple[PlayerDetail, ParentContact | None] | None

_SORT_COLUMNS = {
    "created_at_desc": User.created_at.desc(),
    "created_at_asc": User.created_at.asc(),
    "name_asc": (UserProfile.first_name.asc(), UserProfile.last_name.asc()),
    "name_desc": (UserProfile.first_name.desc(), UserProfile.last_name.desc()),
}


@dataclass
class NewAccountInput:
    role: UserRole
    email: str
    first_name: str
    last_name: str
    phone: str
    business_name: str | None = None


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> User | None:
        """`profile` is eagerly loaded — accessing it lazily after this
        method returns would risk a MissingGreenlet error under the async
        driver, since a bare lazy relationship access performs blocking
        I/O outside the greenlet SQLAlchemy's asyncio extension sets up
        for the query that created this object."""
        result = await self._session.execute(
            select(User).where(User.id == user_id).options(selectinload(User.profile))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email.lower()).options(selectinload(User.profile))
        )
        return result.scalar_one_or_none()

    async def get_profile(self, user_id: str) -> UserProfile | None:
        return await self._session.get(UserProfile, user_id)

    async def any_super_admin_exists(self) -> bool:
        """Regardless of status — backs the bootstrap command's refusal to
        run a second time (it must not mint a second Super Admin even if
        the first was later deactivated)."""
        result = await self._session.execute(
            select(func.count()).where(User.role == UserRole.SUPER_ADMIN.value)
        )
        return result.scalar_one() > 0

    async def count_active_super_admins(self) -> int:
        """Backs the last-active-Super-Admin guard (FR-041). Callers that
        need this to be race-safe under a concurrent second deactivation
        must call it inside the same transaction as the status write
        (research.md R-09) — SQLite serializes write transactions, so a
        count-then-write within one transaction is sufficient here; a
        store with concurrent writers would need an explicit row lock."""
        result = await self._session.execute(
            select(func.count()).where(
                User.role == UserRole.SUPER_ADMIN.value,
                User.status == AccountStatus.ACTIVE.value,
            )
        )
        return result.scalar_one()

    async def insert_account(self, data: NewAccountInput) -> User:
        """Creates the account with its profile and the one role detail
        row matching `data.role` (FR-021, FR-030) — all added to the
        session but not yet flushed, so the caller's service can add the
        audit entry and invitation in the same transaction before it
        commits (FR-024: no partial account on failure)."""
        now = utcnow()
        user = User(
            id=new_uuid(),
            email=data.email.lower(),
            password_hash=None,
            role=data.role.value,
            status=AccountStatus.ACTIVE.value,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(user)
        await self._session.flush()

        self._session.add(
            UserProfile(
                user_id=user.id,
                first_name=data.first_name,
                last_name=data.last_name,
                phone=data.phone,
                updated_at=now,
            )
        )

        if data.role is UserRole.TRAINER:
            assert data.business_name is not None
            self._session.add(
                TrainerOrganization(user_id=user.id, business_name=data.business_name)
            )
        elif data.role is UserRole.COACH:
            self._session.add(CoachDetail(user_id=user.id, is_publicly_visible=False))
        elif data.role is UserRole.PLAYER_PARENT:
            self._session.add(PlayerDetail(user_id=user.id))
            self._session.add(ParentContact(user_id=user.id))

        await self._session.flush()
        return user

    async def get_role_detail(self, user: User) -> RoleDetailRow:
        role = user.role_enum
        if role is UserRole.TRAINER:
            return await self._session.get(TrainerOrganization, user.id)
        if role is UserRole.COACH:
            return await self._session.get(CoachDetail, user.id)
        if role is UserRole.PLAYER_PARENT:
            player = await self._session.get(PlayerDetail, user.id)
            parent = await self._session.get(ParentContact, user.id)
            return (player, parent) if player is not None else None
        return None

    async def list_directory(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None,
        role: UserRole | None,
        status: AccountStatus | None,
        sort: str,
    ) -> tuple[list[tuple[User, UserProfile]], int]:
        base = select(User, UserProfile).join(UserProfile, UserProfile.user_id == User.id)

        if query:
            pattern = f"%{query.lower()}%"
            base = base.where(
                or_(
                    func.lower(User.email).like(pattern),
                    func.lower(UserProfile.first_name).like(pattern),
                    func.lower(UserProfile.last_name).like(pattern),
                )
            )
        if role is not None:
            base = base.where(User.role == role.value)
        if status is not None:
            base = base.where(User.status == status.value)

        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()

        order = _SORT_COLUMNS.get(sort, _SORT_COLUMNS["created_at_desc"])
        order_clauses = order if isinstance(order, tuple) else (order,)
        rows = await self._session.execute(
            base.order_by(*order_clauses).offset((page - 1) * page_size).limit(page_size)
        )
        return [(u, p) for u, p in rows.all()], total

    def apply_status_change(
        self, user: User, *, target_status: AccountStatus, expected_version: int
    ) -> None:
        """Optimistic-concurrency status write (R-10). `user` must already
        be loaded in this same transaction — the version compared here is
        only meaningful if it was read fresh, which every caller does via
        get_by_id at the start of the request.

        SQLite serializes write transactions, so this check-then-write
        inside one transaction is sufficient for correctness (research.md
        R-09); a store with concurrent writers would need an explicit row
        lock between the check and the write.
        """
        if user.version != expected_version:
            raise StaleVersion("This account was changed by someone else. Reload and try again.")
        user.status = target_status.value
        user.version += 1
        user.updated_at = utcnow()
