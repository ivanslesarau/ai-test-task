from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import Conflict, NotFound, PlayerProfileNotFound, ValidationFailure
from app.core.security import generate_token, hash_token
from app.models.enums import AccountStatus, PlayerProfileKind, UserRole
from app.models.player_profile import PlayerProfile
from app.models.user import User
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.player_profile_repository import PlayerProfileRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import NewAccountInput, UserRepository
from app.schemas.child_signin import ChildSignIn, GrantChildSignInRequest
from app.services.ports.email_sender import EmailSender
from app.services.templates.invitation import render_invitation_email


class ChildSigninService:
    """Grant and revoke a child's own sign-in (US11; FR-129, FR-130,
    FR-134, FR-135; data-model.md §26.1).

    `grant` creates an ordinary `player_parent` account for the child —
    "childness" is derived from `player_profiles.sign_in_user_id` naming
    it (research.md R-38), never a role or column of its own — and seeds
    that new account's mandatory `user_profiles` row from the profile,
    because the profile is the one writer of a child's name and
    data-model.md §3 still requires a non-null name on every `users` row
    (data-model.md §26.1, "the one duplication this design accepts"). The
    setup invitation reuses the exact mechanism
    `UserAdminService.create_user` uses for every other invited account —
    a `credential_setup_invitations` row and `render_invitation_email` —
    rather than a second invite path (research.md R-38's "ordinary
    account" framing).

    `revoke` clears the link and revokes every session that account
    holds, under the same session-revocation-by-user
    `UserAdminService.deactivate` already uses (FR-012, FR-134). It never
    touches the profile, its associations, or its history.
    """

    def __init__(
        self, db_session: AsyncSession, settings: Settings, email_sender: EmailSender
    ) -> None:
        self._settings = settings
        self._email_sender = email_sender
        self._users = UserRepository(db_session)
        self._profiles = PlayerProfileRepository(db_session)
        self._sessions = SessionRepository(db_session)
        self._invitations = InvitationRepository(db_session)

    async def _resolve_own_child_profile(self, parent: User, profile_id: str) -> PlayerProfile:
        """Parent-only reachability (research.md R-48) — 404, not 403, for
        a profile that does not exist or belongs to another account."""
        profile = await self._profiles.get_by_id(profile_id)
        if (
            profile is None
            or profile.removed_at is not None
            or profile.account_user_id != parent.id
        ):
            raise PlayerProfileNotFound("No such player profile.")
        if profile.kind != PlayerProfileKind.CHILD.value:
            # A `self` profile's sign-in *is* the account (R-37) — the
            # schema's own `ck_player_profiles_signin_is_child` constraint
            # states the same rule at the database level.
            raise ValidationFailure(
                "A self profile's sign-in is the account itself.",
                fields={"profile_id": "Only a child profile can be granted a sign-in."},
            )
        return profile

    async def grant(
        self, parent: User, profile_id: str, body: GrantChildSignInRequest
    ) -> ChildSignIn:
        profile = await self._resolve_own_child_profile(parent, profile_id)

        # Platform-wide uniqueness across every status (FR-004) — the same
        # check-then-insert convention every other account-creation path in
        # this codebase follows, which is what refuses the parent's own
        # address without a separate, parallel rule (FR-129).
        if await self._users.get_by_email(body.email) is not None:
            raise Conflict("That email address is already in use.")

        # data-model.md §26.1: the profile is authoritative for a child's
        # name; this is the one place that seeds the account's mandatory
        # `user_profiles` row from it. No phone of the child's own is
        # collected — the family's single contact record already lives on
        # the parent (data-model.md §29.3).
        child_user = await self._users.insert_account(
            NewAccountInput(
                role=UserRole.PLAYER_PARENT,
                email=body.email,
                first_name=profile.first_name or "",
                last_name=profile.last_name or "",
                phone=None,
            )
        )

        profile.sign_in_user_id = child_user.id

        raw_token = generate_token()
        await self._invitations.create(
            user_id=child_user.id,
            token_hash=hash_token(raw_token),
            issued_by_user_id=parent.id,
            ttl_hours=self._settings.invitation_ttl_hours,
        )

        setup_url = f"{self._settings.frontend_base_url}/set-password?token={raw_token}"
        subject, mail_body = render_invitation_email(
            first_name=profile.first_name or "",
            setup_url=setup_url,
            ttl_hours=self._settings.invitation_ttl_hours,
        )
        # A delivery failure never rolls back the sign-in already granted,
        # and is never reported to the caller as a success (FR-064) — the
        # boolean is surfaced, not discarded, unlike the join-confirmation
        # email's failure (that one has no recovery step; this one does,
        # by re-granting).
        invitation_sent = await self._email_sender.send(
            to=child_user.email, subject=subject, body=mail_body
        )

        return ChildSignIn(
            player_profile_id=profile.id,
            email=child_user.email,
            invitation_sent=invitation_sent,
        )

    async def revoke(self, parent: User, profile_id: str) -> None:
        profile = await self._resolve_own_child_profile(parent, profile_id)
        if profile.sign_in_user_id is None:
            raise NotFound("This child has no sign-in to revoke.")

        # FR-134: every session dies immediately (the same mechanism
        # FR-012 already uses), and the link is cleared so the account is
        # no longer reachable through `sign_in_user_id`. Clearing the
        # link alone would leave an ordinary, still-Active `player_parent`
        # account behind that could simply sign in again with its
        # existing password — exactly the "convert itself into an
        # independent account" FR-135 forbids for the removal path, and
        # quickstart 11.15's "child cannot sign in" for this one. The
        # child's own `status` is what research.md R-50 reserves for the
        # child's *own* lifecycle (as opposed to the parent-derived
        # suspension check in `AuthService`), so this is the fact that
        # belongs on the child's row, not a second parallel column.
        child_user_id = profile.sign_in_user_id
        profile.sign_in_user_id = None
        await self._sessions.revoke_all_for_user(child_user_id)

        child_user = await self._users.get_by_id(child_user_id)
        if child_user is not None and child_user.status_enum is AccountStatus.ACTIVE:
            self._users.apply_status_change(
                child_user,
                target_status=AccountStatus.INACTIVE,
                expected_version=child_user.version,
            )
