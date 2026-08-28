from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ChildMustAskParent, Conflict, RoleCannotJoin
from app.core.security import generate_token, hash_password, hash_token
from app.models.enums import ApprovalRequestKind, AssociationStatus, PlayerProfileKind, UserRole
from app.models.player_profile import PlayerProfile
from app.models.role_details import TrainerOrganization
from app.models.share_link import ShareLink
from app.models.user import User
from app.repositories.approval_repository import ApprovalRepository
from app.repositories.association_repository import AssociationRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.player_profile_repository import PlayerProfileRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import NewJoinRegistrationInput, UserRepository
from app.schemas.branding import build_portal_branding_out
from app.schemas.join import (
    JoinAcceptRequest,
    JoinLinkPreview,
    JoinLinkPreviewViewer,
    JoinRegistrationRequest,
    JoinResult,
    JoinSelectableProfile,
)
from app.services.ports.email_sender import EmailSender
from app.services.share_link_service import ShareLinkService
from app.services.templates.child_join_request import render_child_join_request_email
from app.services.templates.join_confirmation import render_join_confirmation_email
from app.services.training_context_service import TrainingContextService


class JoinService:
    """Everything reached through an invitation link (US6, US7): the
    public preview, self-service registration, and an already signed-in
    player's acceptance. Registration is one transaction (research.md
    R-23) — account, profile, player profile, active training context,
    parent contact, association, use-count increment, and session all
    succeed together or none do (FR-083).

    Reworked for family accounts (data-model.md §35): every write that
    used to touch `player_details.active_trainer_user_id` now goes
    through `player_profiles` and `active_training_contexts` instead.
    The family-member selection FR-122/Story 13 adds to `accept` is
    **not** implemented here — this rework only moves the existing
    single-profile behaviour onto the new shape (T326); `accept` selects
    the account's SELF profile, or its only profile when there is no
    SELF one, exactly reproducing the one-account-one-player assumption
    the pre-family code made.
    """

    def __init__(
        self, db_session: AsyncSession, settings: Settings, email_sender: EmailSender
    ) -> None:
        self._db_session = db_session
        self._settings = settings
        self._email_sender = email_sender
        self._users = UserRepository(db_session)
        self._profiles = PlayerProfileRepository(db_session)
        self._associations = AssociationRepository(db_session)
        self._sessions = SessionRepository(db_session)
        self._audit = AuditRepository(db_session)
        self._approvals = ApprovalRepository(db_session)
        self._share_links = ShareLinkService(db_session, settings)
        self._context_service = TrainingContextService(db_session)

    async def preview(self, code: str, *, current_user: User | None) -> JoinLinkPreview:
        link, trainer = await self._share_links.resolve_usable_link(code)
        trainer_org = await self._users.get_role_detail(trainer)
        branding = build_portal_branding_out(trainer_org)
        business_name = (
            trainer_org.business_name if isinstance(trainer_org, TrainerOrganization) else ""
        )

        viewer = await self._resolve_viewer(link_trainer_id=trainer.id, current_user=current_user)

        return JoinLinkPreview(
            trainer_display_name=business_name,
            branding=branding,
            viewer=viewer,
        )

    async def _resolve_viewer(
        self, *, link_trainer_id: str, current_user: User | None
    ) -> JoinLinkPreviewViewer:
        if current_user is None:
            return JoinLinkPreviewViewer(state="anonymous")
        if current_user.role_enum is not UserRole.PLAYER_PARENT:
            return JoinLinkPreviewViewer(state="role_cannot_join")

        # research.md R-38: a signed-in child is refused before they ever
        # submit (FR-137) — the preview explains this rather than letting
        # them find out from a 403 on `accept`.
        child_profile = await self._profiles.get_by_sign_in_user_id(current_user.id)
        if child_profile is not None:
            child_rows = await self._associations.list_active_for_player(child_profile.id)
            already_associated = any(trainer.id == link_trainer_id for _, trainer, _ in child_rows)
            state = "already_associated" if already_associated else "child_must_ask_parent"
            return JoinLinkPreviewViewer(state=state)

        rows = await self._associations.list_active_for_account(current_user.id)
        connected_profile_ids = {
            profile.id for _, profile, trainer, _ in rows if trainer.id == link_trainer_id
        }

        profiles = await self._profiles.list_live_for_account(current_user.id)
        children = [p for p in profiles if p.kind == PlayerProfileKind.CHILD.value]
        if children:
            selectable = [
                JoinSelectableProfile(
                    player_profile_id=p.id,
                    display_name=await self._display_name(p),
                    kind=PlayerProfileKind(p.kind),
                    already_associated=p.id in connected_profile_ids,
                )
                for p in profiles
            ]
            return JoinLinkPreviewViewer(
                state="choose_family_members", selectable_profiles=selectable
            )

        already_associated = any(trainer.id == link_trainer_id for _, _, trainer, _ in rows)
        return JoinLinkPreviewViewer(
            state="already_associated" if already_associated else "can_join"
        )

    async def _display_name(self, profile: PlayerProfile) -> str:
        if profile.kind == PlayerProfileKind.CHILD.value:
            return f"{profile.first_name} {profile.last_name}"
        account_profile = await self._users.get_profile(profile.account_user_id)
        assert account_profile is not None
        return f"{account_profile.first_name} {account_profile.last_name}"

    async def _select_join_profiles(
        self, account: User, *, requested_profile_ids: list[str]
    ) -> list[PlayerProfile]:
        """Which profiles `accept` may associate with the new trainer
        (FR-122, Story 13). Named ids are validated against the caller's
        own live profiles — never trusted bare (research.md R-48) — and
        an id naming another account's profile, or a removed one, is
        silently dropped rather than erroring, since the contract makes
        this a selection, not a lookup.

        An empty (or omitted) selection falls back to the account's only
        live profile when it has exactly one, preserving the 1.1.0
        single-implicit-player behaviour (Story 13 scenario 4); with zero
        or several profiles an empty selection associates nobody (Story
        13 scenario 3)."""
        profiles = await self._profiles.list_live_for_account(account.id)
        if not requested_profile_ids:
            return [profiles[0]] if len(profiles) == 1 else []

        by_id = {p.id: p for p in profiles}
        return [by_id[pid] for pid in requested_profile_ids if pid in by_id]

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

        user, profile = await self._users.insert_join_registration(
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
            trainer_user_id=trainer.id, player_profile_id=profile.id, share_link_id=link.id
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
            detail=f"player_profile={profile.id} share_link={link.id}",
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
            associated_profile_ids=[profile.id],
            already_associated_profile_ids=[],
            active_player_profile_id=profile.id,
            active_trainer_id=trainer.id,
        )
        return result, raw_token

    async def accept(
        self, code: str, *, current_user: User, body: JoinAcceptRequest | None = None
    ) -> JoinResult:
        """An already signed-in Player/Parent joining an additional
        trainer (FR-080, FR-122). `body.player_profile_ids` names which
        family members join; `_select_join_profiles` resolves the
        fallback for an omitted or empty selection (Story 13).

        A signed-in child is routed to `_accept_as_child` instead
        (FR-137 – FR-140, T376/T377): no association is created directly,
        an approval request is raised for the parent, and the caller is
        refused with `child_must_ask_parent`."""
        link, trainer = await self._share_links.resolve_usable_link(code)

        if current_user.role_enum is not UserRole.PLAYER_PARENT:
            raise RoleCannotJoin("This link is for players and parents.")

        trainer_org = await self._users.get_role_detail(trainer)
        business_name = (
            trainer_org.business_name if isinstance(trainer_org, TrainerOrganization) else ""
        )

        child_profile = await self._profiles.get_by_sign_in_user_id(current_user.id)
        if child_profile is not None:
            return await self._accept_as_child(
                current_user,
                child_profile,
                link=link,
                trainer=trainer,
                business_name=business_name,
            )

        requested_ids = body.player_profile_ids if body is not None else []
        selected_profiles = await self._select_join_profiles(
            current_user, requested_profile_ids=requested_ids
        )

        associated_ids: list[str] = []
        already_associated_ids: list[str] = []
        for profile in selected_profiles:
            existing = await self._associations.get(
                trainer_user_id=trainer.id, player_profile_id=profile.id
            )
            if existing is not None:
                # No second association, and the link's use count does
                # not rise for this profile (FR-082, FR-068).
                already_associated_ids.append(profile.id)
                continue

            await self._associations.insert(
                trainer_user_id=trainer.id, player_profile_id=profile.id, share_link_id=link.id
            )
            await self._share_links.record_use(link)
            await self._audit.add(
                action="trainer_player_associated",
                actor_user_id=current_user.id,
                target_user_id=trainer.id,
                detail=f"player_profile={profile.id} share_link={link.id}",
            )
            associated_ids.append(profile.id)

        active_player_profile_id: str | None = None
        active_trainer_id: str | None = None
        if associated_ids:
            # The account holder's own profile when it was among those
            # selected, otherwise the first selected child (Story 13
            # scenario 6). The resolve-and-repair pair resolver is also
            # the one place a context is *set* deliberately
            # (research.md R-36) — reusing it here means this genuinely
            # new join is validated against the association just created,
            # the same way any other switch is.
            self_profile = await self._profiles.get_self_for_account(current_user.id)
            context_profile_id = (
                self_profile.id
                if self_profile is not None and self_profile.id in associated_ids
                else associated_ids[0]
            )
            await self._context_service.switch(
                current_user, player_profile_id=context_profile_id, trainer_id=trainer.id
            )
            active_player_profile_id = context_profile_id
            active_trainer_id = trainer.id
        elif already_associated_ids:
            # Nothing new, but the active context is left exactly as it
            # was — only a genuinely new join moves it (US7 acceptance
            # scenario 1 vs. scenario 2).
            (
                _active_profile_id,
                active_trainer_id,
            ) = await self._context_service.resolve_active_context(current_user)

        return JoinResult(
            trainer_id=trainer.id,
            trainer_display_name=business_name,
            associated_profile_ids=associated_ids,
            already_associated_profile_ids=already_associated_ids,
            active_player_profile_id=active_player_profile_id,
            active_trainer_id=active_trainer_id,
        )

    async def _accept_as_child(
        self,
        current_user: User,
        child_profile: PlayerProfile,
        *,
        link: ShareLink,
        trainer: User,
        business_name: str,
    ) -> JoinResult:
        """FR-137 – FR-140: a signed-in child creates no association
        through this endpoint.

        Already connected with this trainer through their own profile →
        told so, nothing raised, nothing emailed (FR-140) — the same
        shape `accept`'s parent path already returns for "already
        associated". Otherwise → an approval request of kind
        `join_trainer` is raised for the parent and the caller is
        refused with `child_must_ask_parent` (FR-137, FR-138). A repeat
        ask for the same (profile, trainer) raises no second request and
        sends no second email: `uq_approval_requests_live` makes the
        first true by construction, and the caught `IntegrityError` is
        what makes the second a no-op (FR-139, research.md R-40, R-51)."""
        existing = await self._associations.get(
            trainer_user_id=trainer.id, player_profile_id=child_profile.id
        )
        if existing is not None and existing.status == AssociationStatus.ACTIVE.value:
            (
                active_profile_id,
                active_trainer_id,
            ) = await self._context_service.resolve_active_context(current_user)
            return JoinResult(
                trainer_id=trainer.id,
                trainer_display_name=business_name,
                associated_profile_ids=[],
                already_associated_profile_ids=[child_profile.id],
                active_player_profile_id=active_profile_id,
                active_trainer_id=active_trainer_id or trainer.id,
            )

        child_display_name = f"{child_profile.first_name} {child_profile.last_name}"

        try:
            # A SAVEPOINT (`begin_nested`), not a full `rollback()` on the
            # outer session: R-40's partial unique index turns a repeat
            # ask into an IntegrityError here, and only the failed insert
            # itself must be undone. A session-wide rollback would also
            # expire every other object this request (and, under a test
            # harness sharing one session across requests, a later one
            # too) still holds, for no reason connected to this insert.
            async with self._db_session.begin_nested():
                await self._approvals.insert(
                    player_profile_id=child_profile.id,
                    parent_user_id=child_profile.account_user_id,
                    kind=ApprovalRequestKind.JOIN_TRAINER.value,
                    trainer_user_id=trainer.id,
                    share_link_id=link.id,
                )
        except IntegrityError:
            # R-40's partial unique index caught a repeat ask — a live
            # request for this exact (profile, kind, trainer) already
            # exists. No second request, no second email (FR-139, R-51).
            pass
        else:
            parent = await self._users.get_by_id(child_profile.account_user_id)
            assert parent is not None
            # No page exists yet for a parent to act on a specific
            # request (a later phase adds one) — the family area is
            # where every pending decision will surface, the same way
            # `render_invitation_email`'s setup_url is built from
            # `frontend_base_url` rather than from anything in the link
            # itself.
            review_url = f"{self._settings.frontend_base_url}/family"
            subject, mail_body = render_child_join_request_email(
                child_display_name=child_display_name,
                trainer_display_name=business_name,
                review_url=review_url,
            )
            # A delivery failure never undoes the request just raised,
            # and is never reported to anyone as a success (FR-064's
            # lesson, applied to a notification rather than an
            # invitation).
            await self._email_sender.send(to=parent.email, subject=subject, body=mail_body)

        raise ChildMustAskParent("Ask your parent to register you with this trainer.")
