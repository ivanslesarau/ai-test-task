from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ActionNotPermitted, NotFound
from app.db.base import utcnow
from app.models.enums import AccountStatus, PlayerProfileKind, UserRole, is_transition_allowed
from app.models.role_details import CoachDetail, ParentContact, TrainerOrganization
from app.models.user import User
from app.repositories.active_training_context_repository import ActiveTrainingContextRepository
from app.repositories.approval_repository import ApprovalRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.erasure_repository import ErasureRepository
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.player_profile_repository import PlayerProfileRepository
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
        self._profiles = PlayerProfileRepository(db_session)
        self._contexts = ActiveTrainingContextRepository(db_session)
        self._approvals = ApprovalRepository(db_session)
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

        logo_key = await self._anonymize_role_detail(user, actor=actor, reason=reason)

        if photo_key:
            await self._photo_storage.delete(photo_key)
            await self._photo_storage.delete(thumbnail_key_for(photo_key))
        if logo_key:
            # A logo identifies the business as directly as its name
            # (data-model.md §20) — unlike business_name, it is removed.
            await self._photo_storage.delete(logo_key)

        await self._sessions.revoke_all_for_user(user.id)
        await self._invitations.supersede_outstanding_for_user(user.id)

        if user.role_enum is UserRole.PLAYER_PARENT:
            # Every signed-in account — the parent and each child sign-in
            # — holds its own row (data-model.md §27); an erased account
            # has no context to be in (data-model.md §30).
            await self._contexts.delete_for_user(user.id)
            # No one can approve for an erased family (FR-157). A no-op
            # for a cascaded child erasure, which is never a request's
            # parent_user_id.
            await self._approvals.expire_all_live_for_parent(user.id)

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

    async def _anonymize_role_detail(self, user: User, *, actor: User, reason: str) -> str | None:
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
        elif role is UserRole.PLAYER_PARENT:
            if isinstance(detail, ParentContact):
                detail.emergency_contact_name = None
                detail.emergency_contact_phone = None
                detail.emergency_contact_relation = None
            # The player fields moved off the role detail onto
            # player_profiles (data-model.md §35) — every profile this
            # account owns is cleared here instead, extending §10/§20's
            # transformation to §30's.
            await self._anonymize_player_profiles(user, actor=actor, reason=reason)

        return None

    async def _anonymize_player_profiles(self, user: User, *, actor: User, reason: str) -> None:
        """data-model.md §30: every `player_profiles` row this account
        owns — live or already soft-removed, since a removed profile's
        history is still read on a trainer's roster — loses its
        identifying data. `skill_level` and `gender` deliberately survive
        for the same reason §20 gives for the account holder: they are
        classifications later epics group by, not identifiers.

        Each profile that granted a child a sign-in has that child
        account erased too, in this same transaction (research.md R-38,
        R-50) — a child account is personal data about a child, and an
        erased family must not leave a signed-in child able to act on
        its behalf."""
        profiles = await self._profiles.list_all_for_account(user.id)
        for player_profile in profiles:
            if player_profile.kind == PlayerProfileKind.CHILD.value:
                # A child's name is not NULLed — ck_player_profiles_self_names
                # requires one, and the roster must still read "Deleted
                # User" (FR-091). A SELF profile's names are already NULL
                # and stay that way; §10 anonymizes the account's own
                # user_profiles row instead.
                player_profile.first_name = "Deleted"
                player_profile.last_name = "User"

            if player_profile.photo_key:
                await self._photo_storage.delete(player_profile.photo_key)
                await self._photo_storage.delete(thumbnail_key_for(player_profile.photo_key))
            player_profile.photo_key = None
            player_profile.date_of_birth = None
            player_profile.school = None
            player_profile.jersey_number = None
            player_profile.tokens_without_approval = False
            player_profile.updated_at = utcnow()

            if player_profile.sign_in_user_id is not None:
                child_user_id = player_profile.sign_in_user_id
                player_profile.sign_in_user_id = None
                child = await self._users.get_by_id(child_user_id)
                if child is not None and child.status_enum is not AccountStatus.DELETED:
                    await self.erase(
                        child.id, actor=actor, expected_version=child.version, reason=reason
                    )

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
