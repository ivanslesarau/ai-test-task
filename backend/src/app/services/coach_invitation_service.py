from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import (
    AccountNotActive,
    ActionNotPermitted,
    CoachAddressMismatch,
    CoachAlreadyAssigned,
    CoachInvitationPending,
    Conflict,
    InvitationLinkInvalid,
    InvitationNotResendable,
    InvitationNotUsable,
    NotFound,
    RoleCannotAccept,
    ValidationFailure,
)
from app.core.password_policy import validate_password
from app.core.security import generate_token, hash_password, hash_token
from app.db.base import utcnow
from app.models.coach_invitation import CoachInvitation
from app.models.enums import (
    AccountStatus,
    CoachInvitationBlockReason,
    CoachInvitationState,
    UserRole,
)
from app.models.role_details import TrainerOrganization
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.coach_invitation_repository import CoachInvitationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import NewAccountInput, UserRepository
from app.schemas.branding import build_portal_branding_out
from app.schemas.coach import (
    CoachInvitationPreview,
    CoachInvitationPreviewTrainer,
    CoachJoinResult,
    CoachRegistrationRequest,
    CoachSummary,
)
from app.schemas.coach_invitation import (
    CoachInvitationOut,
    CoachInvitationPage,
    CoachInvitationPresentedState,
    build_coach_invitation_out,
)
from app.services.ports.email_sender import EmailSender
from app.services.templates.coach_invitation import render_coach_invitation_email

# The full internal precedence of data-model.md §101.1, including
# `superseded` — which `CoachInvitationPresentedState` (the API-facing
# type in schemas/coach_invitation.py) deliberately excludes, because a
# superseded row is never returned to a client. `presented_state` still
# computes it, so the precedence itself stays testable as one function
# (tasks.md T517) rather than split across two.
_PresentedStateAny = Literal["awaiting", "accepted", "expired", "revoked", "blocked", "superseded"]


class CoachInvitationService:
    """The trainer-issuing half of a coach invitation's lifecycle: issue,
    track, resend, revoke (US-01.08 Story 1 — FR-001 – FR-010, FR-023).

    The acceptance half — preview/register/accept, reached by the invited
    person rather than the trainer — is added to this same class by User
    Story 2 (tasks.md T551, the one deliberate cross-story dependency
    tasks.md's Dependencies section records). Every method here therefore
    takes the acting trainer's own `User` row explicitly, rather than
    assuming the one shape of caller US1 alone would need, so US2's
    methods can sit beside these without reshaping them.
    """

    def __init__(
        self, db_session: AsyncSession, settings: Settings, email_sender: EmailSender
    ) -> None:
        self._settings = settings
        self._email_sender = email_sender
        self._invitations = CoachInvitationRepository(db_session)
        self._users = UserRepository(db_session)
        self._sessions = SessionRepository(db_session)
        self._audit = AuditRepository(db_session)

    # --- the one presentation derivation (data-model.md §101.1) -----------

    @staticmethod
    def presented_state(
        invitation: CoachInvitation, *, now: datetime | None = None
    ) -> _PresentedStateAny:
        """Precedence: accepted > revoked > superseded > expired > blocked
        > awaiting. Never mutates the row — `expired` and `blocked` are
        read-time facts, not writes (research.md R2-03)."""
        now = now or utcnow()
        stored = CoachInvitationState(invitation.state)
        if stored is CoachInvitationState.ACCEPTED:
            return "accepted"
        if stored is CoachInvitationState.REVOKED:
            return "revoked"
        if stored is CoachInvitationState.SUPERSEDED:
            return "superseded"
        if invitation.expires_at <= now:
            return "expired"
        if invitation.blocked_at is not None:
            return "blocked"
        return "awaiting"

    async def _build_out(self, invitation: CoachInvitation) -> CoachInvitationOut:
        presented = self.presented_state(invitation)
        # Every call site builds this from a row that is not superseded —
        # `list_for_trainer` already excludes them, and `issue`/`resend`/
        # `revoke` only ever build from a freshly-inserted or just-acted-on
        # row. Asserted rather than silently coerced, so a future caller
        # that breaks the invariant fails loudly instead of leaking a
        # value the contract's `CoachInvitationState` enum does not admit.
        assert presented != "superseded"
        coach = await self._resolve_coach_summary(invitation)
        return build_coach_invitation_out(invitation, presented_state=presented, coach=coach)

    async def _resolve_coach_summary(self, invitation: CoachInvitation) -> CoachSummary | None:
        """`null` in every state but `accepted` (contracts/openapi.yaml
        `CoachInvitation.coach`) — resolved from `accepted_by_user_id`
        rather than cached on the invitation row, so the trainer always
        sees the coach's current name, email, and status."""
        if invitation.accepted_by_user_id is None:
            return None
        user = await self._users.get_by_id(invitation.accepted_by_user_id)
        if user is None:
            return None
        return CoachSummary(
            user_id=user.id,
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            email=user.email,
            status=user.status_enum.value,  # type: ignore[arg-type]
            photo_url=f"/media/photos/{user.profile.photo_key}" if user.profile.photo_key else None,
        )

    # --- issue, list, resend, revoke (FR-001 – FR-010) ---------------------

    async def issue(
        self, trainer: User, *, email: str, invitee_name: str | None, message: str | None
    ) -> CoachInvitationOut:
        """FR-001 – FR-003, FR-007, FR-008, FR-010, FR-023.

        The response never depends on whether `email` already holds an
        account (FR-008): this method never even checks. Every conflict
        that depends on the invited person's account surfaces later, to
        that person, at acceptance (US2)."""
        self._require_active(trainer)
        invited_email = email.lower()

        existing = await self._invitations.find_live_for_email(trainer.id, invited_email)
        if existing is not None:
            raise CoachInvitationPending(
                "An invitation to this address is already awaiting a response.",
                invitation=(await self._build_out(existing)).model_dump(mode="json"),
            )

        invitation = await self._create_and_send(
            trainer, invited_email=invited_email, invitee_name=invitee_name, message=message
        )
        await self._audit.add(
            action="coach_invitation_issued",
            actor_user_id=trainer.id,
            target_user_id=None,
            detail=f"invitation={invitation.id} email={invited_email}",
        )
        return await self._build_out(invitation)

    async def list_for_trainer(
        self,
        trainer_id: str,
        *,
        page: int,
        page_size: int,
        state: CoachInvitationPresentedState | None = None,
    ) -> CoachInvitationPage:
        """FR-004, FR-009. Filtering and pagination happen here, in
        Python, because `expired` and `blocked` are read-time derivations
        rather than stored columns (data-model.md §101.1) — a SQL `WHERE`
        cannot express them. One trainer's own invitations are bounded in
        practice, so deriving the presented state for the whole set and
        then slicing costs nothing a second query would have saved."""
        rows = await self._invitations.list_for_trainer(trainer_id)
        items = [await self._build_out(row) for row in rows]
        if state is not None:
            items = [item for item in items if item.state == state]
        total = len(items)
        start = (page - 1) * page_size
        page_items = items[start : start + page_size]
        return CoachInvitationPage(items=page_items, total=total, page=page, page_size=page_size)

    async def resend(self, trainer: User, invitation_id: str) -> CoachInvitationOut:
        """FR-005, FR-009, FR-010, FR-023. Permitted while the stored
        state is still `awaiting`, whether or not it has expired; refused
        for an invitation that is already accepted, revoked, or
        superseded. Supersede-and-insert happen in the same request's
        transaction, so the previous link and the trainer's list agree
        the instant this returns."""
        self._require_active(trainer)
        current = await self._require_owned(trainer.id, invitation_id)
        if CoachInvitationState(current.state) is not CoachInvitationState.AWAITING:
            raise InvitationNotResendable("This invitation can no longer be resent.")

        new_invitation = await self._create_and_send(
            trainer,
            invited_email=current.invited_email,
            invitee_name=current.invitee_name,
            message=current.message,
        )
        await self._invitations.mark_superseded(current, superseded_by_id=new_invitation.id)
        await self._audit.add(
            action="coach_invitation_resent",
            actor_user_id=trainer.id,
            target_user_id=None,
            detail=f"superseded={current.id} new={new_invitation.id}",
        )
        return await self._build_out(new_invitation)

    async def revoke(self, trainer: User, invitation_id: str) -> CoachInvitationOut:
        """FR-006, FR-009, FR-023. Permitted for a presently live
        invitation — `awaiting` or `blocked` — refused for one that is
        already accepted, revoked, or expired (an expired invitation
        needs no revoking, and saying so is clearer than pretending the
        action did something)."""
        self._require_active(trainer)
        current = await self._require_owned(trainer.id, invitation_id)
        presented = self.presented_state(current)
        if presented not in ("awaiting", "blocked"):
            raise ActionNotPermitted(
                "This invitation can no longer be revoked.", code="invitation_not_revocable"
            )
        await self._invitations.mark_revoked(current)
        await self._audit.add(
            action="coach_invitation_revoked",
            actor_user_id=trainer.id,
            target_user_id=None,
            detail=f"invitation={current.id}",
        )
        return await self._build_out(current)

    # --- preview, register, accept (US2, FR-011 – FR-019, FR-023) ---------
    #
    # Reached by the invited person, never the trainer — the one
    # deliberate cross-story dependency tasks.md's Dependencies section
    # records: US-01.08's two halves share this one invitation aggregate.

    async def preview(self, token: str) -> CoachInvitationPreview:
        """FR-011 – FR-013. Public and unauthenticated (`security: []`) —
        gated on possession of the mailed token, never on a session
        (research.md R2-05). `account_exists` is not the FR-008
        enumeration leak: that rule protects the *trainer* from learning
        whether an address is registered, and this response is gated on a
        256-bit token mailed to that address."""
        invitation, trainer = await self._resolve_usable(token)
        account_exists = await self._users.get_by_email(invitation.invited_email) is not None
        business_name = await self._business_name(trainer)
        trainer_org = await self._users.get_role_detail(trainer)
        branding = build_portal_branding_out(trainer_org)
        return CoachInvitationPreview(
            invited_email=invitation.invited_email,
            invitee_name=invitation.invitee_name,
            message=invitation.message,
            expires_at=invitation.expires_at,
            account_exists=account_exists,
            trainer=CoachInvitationPreviewTrainer(
                business_name=business_name, portal_branding=branding
            ),
        )

    async def register(
        self, token: str, body: CoachRegistrationRequest
    ) -> tuple[CoachJoinResult, str]:
        """FR-011, FR-013, FR-017, FR-018, FR-023. For an invited person
        who holds no account yet. The email is taken from the invitation,
        never from the request body (`CoachRegistrationRequest` carries no
        `email`, `role`, or `trainer_id` field at all) — this is what
        makes FR-013's address binding unbreakable rather than merely
        checked. Returns `(result, raw_session_token)`; the router sets
        the session cookie from the token, exactly as `JoinService.register`
        does."""
        invitation, trainer = await self._resolve_usable(token)

        if await self._users.get_by_email(invitation.invited_email) is not None:
            raise Conflict(
                "An account with this email already exists. Sign in, then open the link again."
            )

        policy_error = validate_password(body.password)
        if policy_error:
            raise ValidationFailure(
                "One or more fields are invalid.", fields={"password": policy_error}
            )

        # Every validation-driven raise above happens before the first
        # write, matching JoinService.register's own convention
        # (db/session.py commits on a DomainError, so a partial write must
        # never sit behind one).
        user = await self._users.insert_account(
            NewAccountInput(
                role=UserRole.COACH,
                email=invitation.invited_email,
                first_name=body.first_name,
                last_name=body.last_name,
                phone=body.phone,
            )
        )
        user.password_hash = hash_password(body.password)

        coach_detail = await self._users.get_coach_detail(user.id)
        assert coach_detail is not None
        coach_detail.bio = body.bio
        coach_detail.credentials = body.credentials
        coach_detail.certifications = body.certifications

        joined_at = utcnow()
        rowcount = await self._invitations.mark_accepted(invitation.id, accepted_by_user_id=user.id)
        if rowcount == 0:
            # FR-018: lost the race — some other request accepted this
            # invitation in the gap between `_resolve_usable` and here.
            # The account already created is not undone (db/session.py
            # commits on a DomainError): the person can still sign in,
            # simply not onto this roster through this link.
            raise InvitationNotUsable("This invitation was just used. Sign in instead.")

        await self._users.assign_coach_to_trainer(
            coach_detail, trainer_user_id=trainer.id, joined_at=joined_at
        )
        await self._invitations.clear_block(invitation)

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
            detail=f"role=coach email={user.email} via_coach_invitation={invitation.id}",
        )
        await self._audit.add(
            action="coach_invitation_accepted",
            actor_user_id=user.id,
            target_user_id=user.id,
            detail=f"invitation={invitation.id} trainer={trainer.id}",
        )

        business_name = await self._business_name(trainer)
        result = CoachJoinResult(
            outcome="joined", trainer_business_name=business_name, joined_at=joined_at
        )
        return result, raw_token

    async def accept(self, token: str, *, current_user: User) -> CoachJoinResult:
        """FR-012 – FR-019, FR-023. For a signed-in account. Checked in
        order: address binding (FR-013), role (FR-014), the FR-016 no-op
        (before the FR-015 branch, data-model.md §111.1), then the
        one-trainer rule (FR-015)."""
        invitation, trainer = await self._resolve_usable(token)

        if current_user.email != invitation.invited_email:
            raise CoachAddressMismatch(f"This invitation was sent to {invitation.invited_email}.")

        if current_user.role_enum is not UserRole.COACH:
            await self._block(
                invitation, current_user, reason=CoachInvitationBlockReason.ROLE_NOT_COACH
            )
            raise RoleCannotAccept("Only a coach account can accept this invitation.")

        coach_detail = await self._users.get_coach_detail(current_user.id)
        assert coach_detail is not None
        business_name = await self._business_name(trainer)

        if coach_detail.trainer_user_id == trainer.id:
            # FR-016: already on THIS trainer's roster — a no-op success,
            # not an error, and no duplicate assignment is written.
            assert coach_detail.joined_at is not None
            return CoachJoinResult(
                outcome="already_on_this_roster",
                trainer_business_name=business_name,
                joined_at=coach_detail.joined_at,
            )

        if coach_detail.trainer_user_id is not None:
            # FR-015: SC-003's non-disclosure line. The block, the audit
            # entry, and the exception message below name no trainer.
            await self._block(
                invitation, current_user, reason=CoachInvitationBlockReason.ALREADY_ASSIGNED
            )
            raise CoachAlreadyAssigned(
                "You already work with a trainer. Leave that trainer before accepting this "
                "invitation."
            )

        joined_at = utcnow()
        rowcount = await self._invitations.mark_accepted(
            invitation.id, accepted_by_user_id=current_user.id
        )
        if rowcount == 0:
            # FR-018: the other side of a concurrent-acceptance race — by
            # the time this call's conditional UPDATE ran, the invitation
            # was no longer `awaiting`. The same 404 every other spent
            # link returns; the caller cannot tell "someone else just
            # took it" from "this was already dead" (and does not need
            # to).
            raise InvitationLinkInvalid("This invitation is no longer valid.")

        await self._users.assign_coach_to_trainer(
            coach_detail, trainer_user_id=trainer.id, joined_at=joined_at
        )
        await self._invitations.clear_block(invitation)

        await self._audit.add(
            action="coach_invitation_accepted",
            actor_user_id=current_user.id,
            target_user_id=current_user.id,
            detail=f"invitation={invitation.id} trainer={trainer.id}",
        )

        return CoachJoinResult(
            outcome="joined", trainer_business_name=business_name, joined_at=joined_at
        )

    async def _block(
        self, invitation: CoachInvitation, current_user: User, *, reason: CoachInvitationBlockReason
    ) -> None:
        """FR-014/FR-015's shared write: the block is an annotation, not a
        state — the invitation stays `awaiting` and usable (§101.2). The
        audit `detail` carries the reason, never the other trainer's
        identity (SC-003)."""
        await self._invitations.set_block(invitation, reason=reason)
        await self._audit.add(
            action="coach_invitation_refused",
            actor_user_id=current_user.id,
            target_user_id=None,
            detail=f"invitation={invitation.id} reason={reason.value}",
        )

    async def _resolve_usable(self, token: str) -> tuple[CoachInvitation, User]:
        """The single refusal path for every reason a coach invitation
        link can be unusable (contracts/openapi.yaml's
        `previewCoachInvitation` description) — unknown token, spent,
        revoked, superseded, expired, or an inviting trainer who is no
        longer Active. One exception, so a stranger cannot learn which
        condition applied."""
        invitation = await self._invitations.get_by_token_hash(hash_token(token))
        if invitation is None or not CoachInvitationRepository.is_usable(invitation):
            raise InvitationLinkInvalid("This invitation is no longer valid.")
        trainer = await self._users.get_by_id(invitation.trainer_user_id)
        if trainer is None or trainer.status_enum is not AccountStatus.ACTIVE:
            raise InvitationLinkInvalid("This invitation is no longer valid.")
        return invitation, trainer

    # --- shared helpers ------------------------------------------------

    def _require_active(self, trainer: User) -> None:
        """FR-010. Defence in depth: `AuthService.authenticate_session`
        already refuses every request from a non-Active account before
        any router runs (it re-checks status on every request, not only
        at sign-in), so this branch is unreachable through the normal
        `TrainerOnlyDep` path today. A service must not assume it is only
        ever invoked through that one dependency chain, so the check
        stays here rather than being dropped as dead code."""
        if trainer.status_enum is not AccountStatus.ACTIVE:
            raise AccountNotActive("Your account must be Active to do this.")

    async def _require_owned(self, trainer_id: str, invitation_id: str) -> CoachInvitation:
        """404, not 403, for an invitation the caller does not own — the
        same "name a resource you do not have" reasoning
        `ApprovalService._require_parent_owned` applies (FR-009)."""
        invitation = await self._invitations.get_by_id(invitation_id)
        if invitation is None or invitation.trainer_user_id != trainer_id:
            raise NotFound("No such invitation.")
        return invitation

    async def _create_and_send(
        self, trainer: User, *, invited_email: str, invitee_name: str | None, message: str | None
    ) -> CoachInvitation:
        raw_token = generate_token()
        expires_at = utcnow() + timedelta(days=self._settings.coach_invitation_ttl_days)
        invitation = await self._invitations.insert(
            trainer_user_id=trainer.id,
            created_by_user_id=trainer.id,
            token_hash=hash_token(raw_token),
            invited_email=invited_email,
            invitee_name=invitee_name,
            message=message,
            expires_at=expires_at,
        )
        business_name = await self._business_name(trainer)
        invite_url = f"{self._settings.frontend_base_url}/coach-invite/{raw_token}"
        subject, body = render_coach_invitation_email(
            business_name=business_name,
            invitee_name=invitee_name,
            message=message,
            invite_url=invite_url,
            expires_at=expires_at,
        )
        # A delivery failure does not roll back the invitation. FR-008
        # forbids the response from ever depending on delivery outcome in
        # the first place — unlike `CreatedUser.invitation_sent`
        # (user_admin_service.py), this response carries no such field at
        # all, so there is nothing for a failed send to change.
        await self._email_sender.send(to=invited_email, subject=subject, body=body)
        return invitation

    async def _business_name(self, trainer: User) -> str:
        detail = await self._users.get_role_detail(trainer)
        if isinstance(detail, TrainerOrganization):
            return detail.business_name
        # Defensive only: every Trainer account carries a
        # TrainerOrganization row by construction (UserAdminService.create_user).
        return f"{trainer.profile.first_name} {trainer.profile.last_name}"
