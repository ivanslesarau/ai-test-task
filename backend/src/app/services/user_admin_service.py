from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ActionNotPermitted, Conflict, NotFound
from app.core.security import generate_token, hash_token
from app.models.enums import AccountStatus, UserRole, is_transition_allowed
from app.models.user import User, UserProfile
from app.repositories.audit_repository import AuditRepository
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import NewAccountInput, UserRepository
from app.schemas.admin_user import (
    AuditActorOut,
    AuditEntryOut,
    CreatedUser,
    UserDetail,
    UserSummary,
)
from app.schemas.role_detail import build_role_detail_out
from app.services.ports.email_sender import EmailSender
from app.services.templates.invitation import render_invitation_email


def _available_actions(*, status: AccountStatus, has_password: bool) -> list[str]:
    if status is AccountStatus.ACTIVE:
        actions = ["deactivate", "erase"]
        if not has_password:
            actions.append("reinvite")
        return actions
    if status is AccountStatus.INACTIVE:
        return ["reactivate", "erase"]
    return []  # Deleted: erasure is terminal (FR-048)


def _to_summary(user: User, profile: UserProfile) -> UserSummary:
    thumbnail_url = (
        f"/media/photos/{profile.photo_key}?variant=thumb" if profile.photo_key else None
    )
    return UserSummary(
        id=user.id,
        email=user.email,
        first_name=profile.first_name,
        last_name=profile.last_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        thumbnail_url=thumbnail_url,
        has_password=user.password_hash is not None,
    )


class UserAdminService:
    def __init__(
        self, db_session: AsyncSession, settings: Settings, email_sender: EmailSender
    ) -> None:
        self._settings = settings
        self._email_sender = email_sender
        self._users = UserRepository(db_session)
        self._invitations = InvitationRepository(db_session)
        self._audit = AuditRepository(db_session)
        self._sessions = SessionRepository(db_session)

    async def create_user(
        self,
        *,
        role: UserRole,
        email: str,
        first_name: str,
        last_name: str,
        phone: str,
        business_name: str | None,
        actor: User,
    ) -> CreatedUser:
        if await self._users.get_by_email(email) is not None:
            raise Conflict("An account with this email address already exists.")

        user = await self._users.insert_account(
            NewAccountInput(
                role=role,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                business_name=business_name,
            )
        )

        await self._audit.add(
            action="user_created",
            actor_user_id=actor.id,
            target_user_id=user.id,
            detail=f"role={role.value} email={user.email}",
        )

        raw_token = generate_token()
        invitation = await self._invitations.create(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            issued_by_user_id=actor.id,
            ttl_hours=self._settings.invitation_ttl_hours,
        )
        await self._audit.add(
            action="invitation_issued",
            actor_user_id=actor.id,
            target_user_id=user.id,
            detail=f"expires_at={invitation.expires_at.isoformat()}",
        )

        setup_url = f"{self._settings.frontend_base_url}/set-password?token={raw_token}"
        subject, body = render_invitation_email(
            first_name=first_name,
            setup_url=setup_url,
            ttl_hours=self._settings.invitation_ttl_hours,
        )
        # A delivery failure does not roll back account creation — the
        # account already exists and re-inviting (FR-028) is the recovery
        # path, exactly as CreatedUser.invitation_sent communicates.
        invitation_sent = await self._email_sender.send(to=user.email, subject=subject, body=body)

        profile = await self._users.get_profile(user.id)
        assert profile is not None
        role_detail = build_role_detail_out(await self._users.get_role_detail(user))

        return CreatedUser(
            user=UserDetail(
                **_to_summary(user, profile).model_dump(),
                version=user.version,
                phone=profile.phone,
                photo_url=None,
                role_detail=role_detail,
                last_login_at=user.last_login_at,
                available_actions=_available_actions(status=user.status_enum, has_password=False),
            ),
            invitation_sent=invitation_sent,
            invitation_expires_at=invitation.expires_at,
        )

    async def list_users(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None,
        role: UserRole | None,
        status: AccountStatus | None,
        sort: str,
    ) -> tuple[list[UserSummary], int]:
        rows, total = await self._users.list_directory(
            page=page, page_size=page_size, query=query, role=role, status=status, sort=sort
        )
        return [_to_summary(u, p) for u, p in rows], total

    async def get_user(self, user_id: str) -> UserDetail:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFound("No such user.")
        profile = await self._users.get_profile(user_id)
        assert profile is not None
        role_detail = build_role_detail_out(await self._users.get_role_detail(user))
        photo_url = f"/media/photos/{profile.photo_key}" if profile.photo_key else None

        return UserDetail(
            **_to_summary(user, profile).model_dump(),
            version=user.version,
            phone=profile.phone,
            photo_url=photo_url,
            role_detail=role_detail,
            last_login_at=user.last_login_at,
            available_actions=_available_actions(
                status=user.status_enum, has_password=user.password_hash is not None
            ),
        )

    async def list_audit(
        self, user_id: str, *, page: int, page_size: int
    ) -> tuple[list[AuditEntryOut], int]:
        entries, total = await self._audit.list_for_target(user_id, page=page, page_size=page_size)

        actor_ids = {e.actor_user_id for e in entries if e.actor_user_id is not None}
        actor_names: dict[str, str] = {}
        for actor_id in actor_ids:
            profile = await self._users.get_profile(actor_id)
            if profile is not None:
                actor_names[actor_id] = f"{profile.first_name} {profile.last_name}"

        items = [
            AuditEntryOut(
                id=e.id,
                action=e.action,
                actor=AuditActorOut(
                    id=e.actor_user_id,
                    display_name=actor_names.get(e.actor_user_id, "Unknown"),
                )
                if e.actor_user_id
                else None,
                reason=e.reason,
                detail=e.detail,
                occurred_at=e.occurred_at,
            )
            for e in entries
        ]
        return items, total

    async def deactivate(self, user_id: str, *, actor: User, expected_version: int) -> UserDetail:
        if user_id == actor.id:
            raise ActionNotPermitted(
                "You cannot deactivate your own account.", code="self_action_forbidden"
            )
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFound("No such user.")
        if not is_transition_allowed(user.status_enum, AccountStatus.INACTIVE):
            raise ActionNotPermitted(
                "This account cannot be deactivated from its current status.",
                code="invalid_status_transition",
            )
        if (
            user.role_enum is UserRole.SUPER_ADMIN
            and (await self._users.count_active_super_admins()) <= 1
        ):
            raise ActionNotPermitted(
                "This is the only active Super Admin and cannot be deactivated.",
                code="last_super_admin",
            )

        self._users.apply_status_change(
            user, target_status=AccountStatus.INACTIVE, expected_version=expected_version
        )
        # Revoked in the same transaction as the status write, so access
        # dies immediately rather than at the session's natural expiry
        # (FR-012, SC-007).
        await self._sessions.revoke_all_for_user(user.id)
        await self._audit.add(
            action="user_deactivated", actor_user_id=actor.id, target_user_id=user.id
        )
        return await self.get_user(user.id)

    async def reactivate(self, user_id: str, *, actor: User, expected_version: int) -> UserDetail:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFound("No such user.")
        if user.status_enum is AccountStatus.DELETED:
            raise ActionNotPermitted(
                "This account was erased and cannot be reactivated.",
                code="erasure_is_permanent",
            )
        if not is_transition_allowed(user.status_enum, AccountStatus.ACTIVE):
            raise ActionNotPermitted(
                "Only an Inactive account can be reactivated.",
                code="invalid_status_transition",
            )

        self._users.apply_status_change(
            user, target_status=AccountStatus.ACTIVE, expected_version=expected_version
        )
        await self._audit.add(
            action="user_reactivated", actor_user_id=actor.id, target_user_id=user.id
        )
        return await self.get_user(user.id)

    async def reinvite(self, user_id: str, *, actor: User) -> tuple[bool, datetime]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFound("No such user.")
        if user.password_hash is not None:
            raise ActionNotPermitted(
                "This account already has a password set.", code="already_has_password"
            )
        if user.status_enum is not AccountStatus.ACTIVE:
            raise ActionNotPermitted(
                "Only an Active account can be re-invited.", code="account_not_active"
            )

        await self._invitations.supersede_outstanding_for_user(user.id)

        raw_token = generate_token()
        invitation = await self._invitations.create(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            issued_by_user_id=actor.id,
            ttl_hours=self._settings.invitation_ttl_hours,
        )
        await self._audit.add(
            action="invitation_issued",
            actor_user_id=actor.id,
            target_user_id=user.id,
            detail=f"reinvite expires_at={invitation.expires_at.isoformat()}",
        )

        profile = await self._users.get_profile(user.id)
        assert profile is not None
        setup_url = f"{self._settings.frontend_base_url}/set-password?token={raw_token}"
        subject, body = render_invitation_email(
            first_name=profile.first_name,
            setup_url=setup_url,
            ttl_hours=self._settings.invitation_ttl_hours,
        )
        invitation_sent = await self._email_sender.send(to=user.email, subject=subject, body=body)

        return invitation_sent, invitation.expires_at
