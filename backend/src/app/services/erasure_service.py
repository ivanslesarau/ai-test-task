from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ActionNotPermitted, NotFound
from app.db.base import utcnow
from app.models.enums import AccountStatus, UserRole, is_transition_allowed
from app.models.role_details import CoachDetail, TrainerOrganization
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.erasure_repository import ErasureRepository
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.share_link_repository import ShareLinkRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin_user import AuditActorOut, ErasureRecordOut, UserDetail
from app.services.ports.photo_storage import PhotoStorage, thumbnail_key_for
from app.services.user_admin_service import UserAdminService


def _placeholder_email(user_id: str) -> str:
    return f"deleted_{user_id}@example.com"


class ErasureService:
    """Privacy erasure (US5). Anonymizes the account row in place rather
    than deleting it — history and reporting totals must survive exactly
    (FR-046, FR-047), which requires the row to keep existing for foreign
    keys to resolve (data-model.md §10, research.md R-08)."""

    def __init__(
        self,
        db_session: AsyncSession,
        photo_storage: PhotoStorage,
        admin_service: UserAdminService,
    ) -> None:
        self._users = UserRepository(db_session)
        self._sessions = SessionRepository(db_session)
        self._invitations = InvitationRepository(db_session)
        self._erasure = ErasureRepository(db_session)
        self._audit = AuditRepository(db_session)
        self._share_links = ShareLinkRepository(db_session)
        self._photo_storage = photo_storage
        self._admin_service = admin_service

    async def erase(
        self, user_id: str, *, actor: User, expected_version: int, reason: str
    ) -> UserDetail:
        if user_id == actor.id:
            raise ActionNotPermitted(
                "You cannot erase your own account.", code="self_action_forbidden"
            )

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFound("No such user.")

        if not is_transition_allowed(user.status_enum, AccountStatus.DELETED):
            raise ActionNotPermitted(
                "This account has already been erased.", code="invalid_status_transition"
            )

        if (
            user.role_enum is UserRole.SUPER_ADMIN
            and (await self._users.count_active_super_admins()) <= 1
        ):
            raise ActionNotPermitted(
                "This is the only active Super Admin and cannot be erased.",
                code="last_super_admin",
            )

        self._users.apply_status_change(
            user, target_status=AccountStatus.DELETED, expected_version=expected_version
        )

        original_email = user.email
        profile = await self._users.get_profile(user.id)
        assert profile is not None
        original_first_name = profile.first_name
        original_last_name = profile.last_name
        photo_key = profile.photo_key

        # data-model.md §10's transformation table, applied in one
        # transaction with the status write above.
        user.email = _placeholder_email(user.id)
        user.password_hash = None

        profile.first_name = "Deleted"
        profile.last_name = "User"
        profile.phone = None
        profile.photo_key = None
        profile.updated_at = utcnow()

        logo_key = await self._anonymize_role_detail(user)

        if photo_key:
            await self._photo_storage.delete(photo_key)
            await self._photo_storage.delete(thumbnail_key_for(photo_key))
        if logo_key:
            # A logo identifies the business as directly as its name
            # (data-model.md §20) — unlike business_name, it is removed.
            await self._photo_storage.delete(logo_key)

        await self._sessions.revoke_all_for_user(user.id)
        await self._invitations.supersede_outstanding_for_user(user.id)

        await self._erasure.add(
            user_id=user.id,
            original_email=original_email,
            original_first_name=original_first_name,
            original_last_name=original_last_name,
            erased_by_user_id=actor.id,
            reason=reason,
        )
        await self._audit.add(
            action="user_erased",
            actor_user_id=actor.id,
            target_user_id=user.id,
            reason=reason,
        )

        return await self._admin_service.get_user(user.id)

    async def _anonymize_role_detail(self, user: User) -> str | None:
        """Returns the trainer's logo key to delete from storage, if any
        (data-model.md §20). Every other side effect happens in place."""
        detail = await self._users.get_role_detail(user)
        role = user.role_enum

        if role is UserRole.TRAINER and isinstance(detail, TrainerOrganization):
            # business_name and primary_color deliberately survive — see
            # data-model.md §10/§20's note: business_name is the entity
            # later epics' revenue and roster records attribute to, and a
            # colour identifies nobody. The logo does identify the
            # business, so it is cleared (its file removed by the caller).
            detail.address = None
            detail.website = None
            detail.description = None
            logo_key = detail.logo_key
            detail.logo_key = None
            detail.branding_updated_at = utcnow()

            # The trainer is gone — every standing link must stop
            # admitting anyone (FR-070), while associations it already
            # produced stay untouched (FR-069).
            current_link = await self._share_links.get_current_for_trainer(user.id)
            if current_link is not None:
                await self._share_links.revoke(current_link)

            return logo_key
        elif role is UserRole.COACH and isinstance(detail, CoachDetail):
            detail.bio = None
            detail.credentials = None
            detail.certifications = None
            detail.is_publicly_visible = False
        elif role is UserRole.PLAYER_PARENT and isinstance(detail, tuple):
            player, parent = detail
            player.school = None
            player.jersey_number = None
            # player.skill_level and player.gender deliberately survive —
            # classifications, not identifiers, and reporting
            # distributions depend on them. is_self is unchanged for the
            # same reason. player_name and date_of_birth are identifying
            # and are cleared; active_trainer_user_id is cleared because
            # an erased account has no context to be in (data-model.md §20).
            player.player_name = None
            player.date_of_birth = None
            player.active_trainer_user_id = None
            if parent is not None:
                parent.emergency_contact_name = None
                parent.emergency_contact_phone = None
                parent.emergency_contact_relation = None

        return None

    async def get_erasure_record(self, user_id: str) -> ErasureRecordOut:
        record = await self._erasure.get_for_user(user_id)
        if record is None:
            raise NotFound("No erasure record exists for this account.")

        erased_by_profile = await self._users.get_profile(record.erased_by_user_id)
        display_name = (
            f"{erased_by_profile.first_name} {erased_by_profile.last_name}"
            if erased_by_profile
            else "Unknown"
        )

        return ErasureRecordOut(
            user_id=record.user_id,
            original_email=record.original_email,
            original_first_name=record.original_first_name,
            original_last_name=record.original_last_name,
            erased_by=AuditActorOut(id=record.erased_by_user_id, display_name=display_name),
            reason=record.reason,
            erased_at=record.erased_at,
        )
