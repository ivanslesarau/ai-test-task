from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import Conflict, RoleCannotJoin
from app.core.security import generate_token, hash_password, hash_token
from app.models.enums import UserRole
from app.models.role_details import TrainerOrganization
from app.models.user import User
from app.repositories.association_repository import AssociationRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import NewJoinRegistrationInput, UserRepository
from app.schemas.branding import build_portal_branding_out
from app.schemas.join import (
    JoinLinkPreview,
    JoinLinkPreviewViewer,
    JoinRegistrationRequest,
    JoinResult,
)
from app.services.ports.email_sender import EmailSender
from app.services.share_link_service import ShareLinkService
from app.services.templates.join_confirmation import render_join_confirmation_email


class JoinService:
    """Everything reached through an invitation link (US6, US7): the
    public preview, self-service registration, and an already signed-in
    player's acceptance. Registration is one transaction (research.md
    R-23) — account, profile, player detail, parent contact, association,
    use-count increment, and session all succeed together or none do
    (FR-083)."""

    def __init__(
        self, db_session: AsyncSession, settings: Settings, email_sender: EmailSender
    ) -> None:
        self._settings = settings
        self._email_sender = email_sender
        self._users = UserRepository(db_session)
        self._associations = AssociationRepository(db_session)
        self._sessions = SessionRepository(db_session)
        self._audit = AuditRepository(db_session)
        self._share_links = ShareLinkService(db_session, settings)

    async def preview(self, code: str, *, current_user: User | None) -> JoinLinkPreview:
        link, trainer = await self._share_links.resolve_usable_link(code)
        trainer_org = await self._users.get_role_detail(trainer)
        branding = build_portal_branding_out(trainer_org)
        business_name = (
            trainer_org.business_name if isinstance(trainer_org, TrainerOrganization) else ""
        )

        state = await self._viewer_state(link_trainer_id=trainer.id, current_user=current_user)

        return JoinLinkPreview(
            trainer_display_name=business_name,
            branding=branding,
            viewer=JoinLinkPreviewViewer(state=state),
        )

    async def _viewer_state(self, *, link_trainer_id: str, current_user: User | None) -> str:
        if current_user is None:
            return "anonymous"
        if current_user.role_enum is not UserRole.PLAYER_PARENT:
            return "role_cannot_join"
        existing = await self._associations.get(
            trainer_user_id=link_trainer_id, player_user_id=current_user.id
        )
        return "already_associated" if existing is not None else "can_join"

    async def register(
        self, code: str, body: JoinRegistrationRequest, *, client_ip: str
    ) -> tuple[JoinResult, str]:
        """Returns (result, raw_session_token) — the router sets the
        session cookie from the token, admitting the person without a
        second sign-in step (FR-078)."""
        link, trainer = await self._share_links.resolve_usable_link(code)

        # Check-then-insert, matching UserAdminService.create_user's
        # established convention in this codebase: every write below
        # happens only after every validation-driven raise point, so a
        # DomainError never fires with a partial write already made
        # (db/session.py commits on DomainError; FR-083 depends on this
        # ordering, not on catching a mid-transaction IntegrityError).
        if await self._users.get_by_email(body.email) is not None:
            raise Conflict(
                "An account with this email already exists. Sign in, then open the link again."
            )

        user = await self._users.insert_join_registration(
            NewJoinRegistrationInput(
                email=body.email,
                password_hash=hash_password(body.password),
                first_name=body.first_name,
                last_name=body.last_name,
                phone=body.phone,
                is_self=body.is_self,
                player_name=body.player_name,
                date_of_birth=body.date_of_birth,
                gender=body.gender.value,
                active_trainer_user_id=trainer.id,
            )
        )

        await self._associations.insert(
            trainer_user_id=trainer.id, player_user_id=user.id, share_link_id=link.id
        )
        await self._share_links.record_use(link)

        raw_token = generate_token()
        await self._sessions.create(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            idle_days=self._settings.session_idle_days,
        )

        await self._audit.add(
            action="user_created",
            actor_user_id=user.id,
            target_user_id=user.id,
            detail=f"role=player_parent email={user.email} via_share_link={link.id}",
        )
        await self._audit.add(
            action="trainer_player_associated",
            actor_user_id=user.id,
            target_user_id=trainer.id,
            detail=f"player={user.id} share_link={link.id}",
        )

        trainer_org = await self._users.get_role_detail(trainer)
        business_name = (
            trainer_org.business_name if isinstance(trainer_org, TrainerOrganization) else ""
        )

        # A delivery failure must not undo the registration or the
        # association, and is never reported to the person as a success
        # (FR-079) — the boolean is discarded, not surfaced in JoinResult.
        subject, mail_body = render_join_confirmation_email(
            first_name=body.first_name, trainer_display_name=business_name
        )
        await self._email_sender.send(to=user.email, subject=subject, body=mail_body)

        result = JoinResult(
            trainer_id=trainer.id,
            trainer_display_name=business_name,
            already_associated=False,
            active_trainer_id=trainer.id,
        )
        return result, raw_token

    async def accept(self, code: str, *, current_user: User) -> JoinResult:
        """An already signed-in Player/Parent joining an additional
        trainer (FR-080). No detail to supply — the account already
        exists."""
        link, trainer = await self._share_links.resolve_usable_link(code)

        if current_user.role_enum is not UserRole.PLAYER_PARENT:
            raise RoleCannotJoin("This link is for players and parents.")

        trainer_org = await self._users.get_role_detail(trainer)
        business_name = (
            trainer_org.business_name if isinstance(trainer_org, TrainerOrganization) else ""
        )

        existing = await self._associations.get(
            trainer_user_id=trainer.id, player_user_id=current_user.id
        )
        if existing is not None:
            # No second association, the link's use count does not rise
            # (FR-082), and the active context is left exactly as it was
            # — only a genuinely new join moves it (US7 acceptance
            # scenario 1 vs. scenario 2).
            player_detail = await self._users.get_role_detail(current_user)
            current_context = (
                player_detail[0].active_trainer_user_id
                if isinstance(player_detail, tuple)
                else None
            )
            return JoinResult(
                trainer_id=trainer.id,
                trainer_display_name=business_name,
                already_associated=True,
                active_trainer_id=current_context or trainer.id,
            )

        await self._associations.insert(
            trainer_user_id=trainer.id, player_user_id=current_user.id, share_link_id=link.id
        )
        await self._share_links.record_use(link)

        player_detail = await self._users.get_role_detail(current_user)
        if isinstance(player_detail, tuple):
            player, _ = player_detail
            player.active_trainer_user_id = trainer.id

        await self._audit.add(
            action="trainer_player_associated",
            actor_user_id=current_user.id,
            target_user_id=trainer.id,
            detail=f"player={current_user.id} share_link={link.id}",
        )

        return JoinResult(
            trainer_id=trainer.id,
            trainer_display_name=business_name,
            already_associated=False,
            active_trainer_id=trainer.id,
        )
