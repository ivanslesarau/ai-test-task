from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ImpersonationNotPermitted, NotFound
from app.core.principal import ImpersonationContext, Principal
from app.db.base import utcnow
from app.models.auth import Session as SessionModel
from app.models.enums import AccountStatus, ImpersonationEndReason, UserRole
from app.models.impersonation import ImpersonationSession
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.impersonation_repository import ImpersonationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.impersonation import ImpersonationOut, ImpersonationPage, ImpersonationParticipant

_NOTICE_WINDOW_SECONDS = 120


class ImpersonationService:
    """Super Admin impersonation — start, resolve-per-request, end, and
    history (US-01.07, FR-040 – FR-056, research.md R2-14 – R2-20).

    `resolve_for_session` is called once per request, from `get_principal`
    (`core/deps.py`) — it is the single place an impersonation ends
    (research.md R2-19), whether by the admin's own action or by the
    request-time checks (deadline, erasure, deactivation) this method
    performs. `start` and `end` (the exit route) are the two other writers
    of `impersonation_sessions`; nothing else in the codebase may touch it.
    """

    def __init__(self, db_session: AsyncSession, settings: Settings) -> None:
        self._settings = settings
        self._users = UserRepository(db_session)
        self._sessions = SessionRepository(db_session)
        self._impersonations = ImpersonationRepository(db_session)
        self._audit = AuditRepository(db_session)

    # --- Pure rules (unit-tested directly, no db_session needed) --------

    @staticmethod
    def check_start_permitted(*, admin_id: str, target: User) -> None:
        """FR-042: refuses a Super Admin target, the caller themselves, or
        an already-erased account, with a single `ImpersonationNotPermitted`
        — before any row is written. An Inactive target is permitted
        (`AccountStatus.DELETED` is the only status this refuses)."""
        if target.id == admin_id:
            raise ImpersonationNotPermitted("You cannot impersonate your own account.")
        if target.status_enum is AccountStatus.DELETED:
            raise ImpersonationNotPermitted("This account cannot be impersonated.")
        if target.role_enum is UserRole.SUPER_ADMIN:
            raise ImpersonationNotPermitted("A Super Admin cannot be impersonated.")

    @staticmethod
    def select_auto_end_reason(
        record: ImpersonationSession, target: User | None, *, now: datetime
    ) -> ImpersonationEndReason | None:
        """The three end reasons `get_principal` can discover on its own,
        in priority order (research.md R2-19): the one-hour deadline
        (`timed_out`), the target having been erased (`target_erased`),
        and the target having left Active status **when it was Active at
        the start** (`target_deactivated`) — read literally, an
        impersonation that began on an Inactive account is not ended
        merely by that account still being Inactive, since it never left
        Active to begin with. `None` means the impersonation is still
        live."""
        if now >= record.expires_at:
            return ImpersonationEndReason.TIMED_OUT
        if target is None or target.status_enum is AccountStatus.DELETED:
            return ImpersonationEndReason.TARGET_ERASED
        if (
            record.target_status_at_start == AccountStatus.ACTIVE.value
            and target.status_enum is not AccountStatus.ACTIVE
        ):
            return ImpersonationEndReason.TARGET_DEACTIVATED
        return None

    # --- Starting and ending -------------------------------------------

    async def start(
        self, *, admin: User, target_user_id: str, session_record: SessionModel
    ) -> ImpersonationOut:
        """FR-040 – FR-042, FR-048, FR-051. `check_start_permitted` refuses
        a Super Admin target, the caller, or an erased account before any
        row is written. An Inactive target is permitted (FR-042) and
        recorded as such via `target_status_at_start`, which is what makes
        FR-050's "leaves Active status" computable later (research.md
        R2-19)."""
        target = await self._users.get_by_id(target_user_id)
        if target is None:
            raise NotFound("No such user.")
        self.check_start_permitted(admin_id=admin.id, target=target)

        # FR-048: at most one open impersonation per admin — superseding
        # the previous one, atomically, before the new row exists at all.
        existing_open = await self._impersonations.get_open_for_admin(admin.id)
        if existing_open is not None:
            await self._close(
                existing_open, reason=ImpersonationEndReason.SUPERSEDED, actor_id=admin.id
            )
            await self._sessions.clear_impersonation_pointer(existing_open.id)

        started_at = utcnow()
        record = await self._impersonations.insert(
            admin_user_id=admin.id,
            target_user_id=target.id,
            auth_session_id=session_record.id,
            target_status_at_start=target.status,
            started_at=started_at,
            expires_at=started_at + timedelta(minutes=self._settings.impersonation_max_minutes),
        )
        session_record.impersonation_id = record.id

        # Actor is the admin, acting under their own identity to start the
        # impersonation — impersonator_user_id stays NULL for this entry
        # (data-model.md §108); dual attribution begins with the very next
        # request, once `get_principal` stamps it.
        await self._audit.add(
            action="impersonation_started",
            actor_user_id=admin.id,
            target_user_id=target.id,
            detail=f"target_status_at_start={target.status}",
        )

        return await self._to_out(record)

    async def end(
        self, *, real_user: User, context: ImpersonationContext, session_record: SessionModel
    ) -> None:
        """FR-045, FR-051: the exit route. Closed as `exited` — the one
        end reason the admin themselves chooses."""
        record = await self._impersonations.get_by_id(context.id)
        if record is None or record.ended_at is not None:
            raise NotFound("No impersonation is in progress.")
        await self._close(record, reason=ImpersonationEndReason.EXITED, actor_id=real_user.id)
        session_record.impersonation_id = None

    async def _close(
        self, record: ImpersonationSession, *, reason: ImpersonationEndReason, actor_id: str
    ) -> None:
        await self._impersonations.close(record, end_reason=reason)
        await self._audit.add(
            action="impersonation_ended",
            actor_user_id=actor_id,
            target_user_id=record.target_user_id,
            detail=f"end_reason={reason.value}",
        )

    # --- Per-request resolution ------------------------------------------

    async def resolve_for_session(self, real_user: User, session_record: SessionModel) -> Principal:
        """The one place an impersonation ends on its own (research.md
        R2-19), called once per request by `get_principal`. Checks, in
        order: the one-hour deadline (`timed_out`), the target having been
        erased (`target_erased`), and the target having left Active status
        **when it was Active at the start** (`target_deactivated`) — an
        impersonation that began on an Inactive account is not ended
        merely by that account still being Inactive."""
        if session_record.impersonation_id is None:
            return Principal(effective_user=real_user, real_user=real_user, impersonation=None)

        record = await self._impersonations.get_by_id(session_record.impersonation_id)
        if record is None or record.ended_at is not None:
            # A pointer to a closed (or nonexistent) row: the §106
            # invariant says this should never happen, but the resolver
            # degrades to the safe reading rather than a stuck
            # impersonation if it ever does (research.md R2-14).
            session_record.impersonation_id = None
            return Principal(effective_user=real_user, real_user=real_user, impersonation=None)

        now = utcnow()
        target = await self._users.get_by_id(record.target_user_id)
        end_reason = self.select_auto_end_reason(record, target, now=now)

        if end_reason is not None:
            await self._close(record, reason=end_reason, actor_id=real_user.id)
            session_record.impersonation_id = None
            return Principal(effective_user=real_user, real_user=real_user, impersonation=None)

        assert target is not None
        context = ImpersonationContext(
            id=record.id,
            admin_user_id=record.admin_user_id,
            target_user_id=record.target_user_id,
            target_status_at_start=record.target_status_at_start,
            started_at=record.started_at,
            expires_at=record.expires_at,
        )
        return Principal(effective_user=target, real_user=real_user, impersonation=context)

    # --- Lifecycle hooks (called from other services) --------------------

    async def close_for_signed_out_session(self, session_record: SessionModel) -> None:
        """`AuthService.sign_out` (data-model.md §114): closes an open
        impersonation riding this session, before the session itself is
        revoked."""
        if session_record.impersonation_id is None:
            return
        record = await self._impersonations.get_by_id(session_record.impersonation_id)
        if record is None or record.ended_at is not None:
            session_record.impersonation_id = None
            return
        await self._close(
            record, reason=ImpersonationEndReason.SIGNED_OUT, actor_id=record.admin_user_id
        )
        session_record.impersonation_id = None

    async def close_for_deactivated_account(self, user_id: str) -> None:
        """`UserAdminService.deactivate` (data-model.md §114): ends any
        open impersonation whose target this account is
        (`target_deactivated`) or whose admin this account is
        (`admin_deactivated`), in the same transaction as the status
        change and the existing session revocation."""
        as_admin = await self._impersonations.get_open_for_admin(user_id)
        if as_admin is not None:
            await self._close(
                as_admin, reason=ImpersonationEndReason.ADMIN_DEACTIVATED, actor_id=user_id
            )
            await self._sessions.clear_impersonation_pointer(as_admin.id)

        as_target = await self._impersonations.get_open_for_target(user_id)
        if as_target is not None:
            await self._close(
                as_target,
                reason=ImpersonationEndReason.TARGET_DEACTIVATED,
                actor_id=as_target.admin_user_id,
            )
            await self._sessions.clear_impersonation_pointer(as_target.id)

    async def close_for_erased_account(self, user_id: str) -> None:
        """`ErasureService.erase` (data-model.md §114): ends any open
        impersonation of the erased account as `target_erased`, keeping
        the history row (FR-039, FR-050, FR-055)."""
        as_target = await self._impersonations.get_open_for_target(user_id)
        if as_target is not None:
            await self._close(
                as_target,
                reason=ImpersonationEndReason.TARGET_ERASED,
                actor_id=as_target.admin_user_id,
            )
            await self._sessions.clear_impersonation_pointer(as_target.id)

    # --- Read paths --------------------------------------------------------

    async def get_current(self, context: ImpersonationContext) -> ImpersonationOut:
        record = await self._impersonations.get_by_id(context.id)
        assert record is not None
        return await self._to_out(record)

    async def get_recently_ended(self, admin_user_id: str) -> ImpersonationOut | None:
        """research.md R2-20: derived from a 120-second look-back over the
        admin's most recently closed impersonation, excluding `exited` —
        the admin who clicked Exit does not need to be told they clicked
        Exit."""
        record = await self._impersonations.most_recent_ended_for_admin(admin_user_id)
        if record is None or record.ended_at is None:
            return None
        if record.end_reason == ImpersonationEndReason.EXITED.value:
            return None
        if (utcnow() - record.ended_at).total_seconds() > _NOTICE_WINDOW_SECONDS:
            return None
        return await self._to_out(record)

    async def history(
        self,
        *,
        admin_user_id: str | None,
        target_user_id: str | None,
        started_from: datetime | None,
        started_to: datetime | None,
        page: int,
        page_size: int,
    ) -> ImpersonationPage:
        """FR-053, FR-054. Built for US7's router; not called by anything
        in this phase."""
        rows, total = await self._impersonations.list_filtered(
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            started_from=started_from,
            started_to=started_to,
            page=page,
            page_size=page_size,
        )
        items = [await self._to_out(record) for record in rows]
        return ImpersonationPage(items=items, total=total, page=page, page_size=page_size)

    # --- Shared building ----------------------------------------------------

    async def _participant(self, user: User) -> ImpersonationParticipant:
        profile = await self._users.get_profile(user.id)
        display_name = f"{profile.first_name} {profile.last_name}" if profile else "Unknown"
        return ImpersonationParticipant(user_id=user.id, display_name=display_name, role=user.role)

    async def _to_out(self, record: ImpersonationSession) -> ImpersonationOut:
        admin = await self._users.get_by_id(record.admin_user_id)
        target = await self._users.get_by_id(record.target_user_id)
        assert admin is not None
        assert target is not None

        duration_seconds: int | None = None
        if record.ended_at is not None:
            duration_seconds = int((record.ended_at - record.started_at).total_seconds())

        return ImpersonationOut(
            id=record.id,
            admin=await self._participant(admin),
            target=await self._participant(target),
            target_status_at_start=record.target_status_at_start,
            started_at=record.started_at,
            expires_at=record.expires_at,
            ended_at=record.ended_at,
            end_reason=record.end_reason,
            duration_seconds=duration_seconds,
        )
