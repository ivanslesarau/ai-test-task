from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import (
    ApprovalAmountChanged,
    ApprovalKindNotExecutable,
    NotFound,
    RequestAlreadyResolved,
)
from app.models.approval import ApprovalRequest
from app.models.enums import ApprovalRequestKind, ApprovalRequestStatus, PlayerProfileKind
from app.models.player_profile import PlayerProfile
from app.models.role_details import TrainerOrganization
from app.repositories.approval_repository import ApprovalRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.player_profile_repository import PlayerProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.approval import ApprovalRequest as ApprovalRequestOut
from app.schemas.approval import ApprovalRequestPage
from app.services.approval_executors import get_executor
from app.services.ports.email_sender import EmailSender
from app.services.templates.approval_decided import render_approval_decided_email
from app.services.templates.approval_expired import (
    render_approval_expired_email_to_child,
    render_approval_expired_email_to_parent,
)

_LIVE_STATUS_VALUES = [
    ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value,
    ApprovalRequestStatus.INFO_REQUESTED.value,
]


def approval_required(kind: ApprovalRequestKind, *, tokens_without_approval: bool) -> bool:
    """The rule matrix `create` consults (FR-145, FR-146; tests/unit/
    test_approval_rules.py, SC-035/SC-036). `tokens_without_approval` is
    read once, here, at creation time — never again at resolution
    (FR-147, research.md R-44), which is what makes a later change to the
    setting leave every already-pending request untouched.

    * `usd_payment` — always `True`. No parameter, anywhere, waives this
      (FR-145); the setting is not even consulted for this kind.
    * `token_spend` — `True` exactly when the setting is off.
    * `join_trainer` — always `True`. The only path that raises this kind
      today (`JoinService._accept_as_child`) exists precisely because the
      child was blocked (FR-137, FR-138); there is no "waived" case."""
    if kind is ApprovalRequestKind.USD_PAYMENT:
        return True
    if kind is ApprovalRequestKind.TOKEN_SPEND:
        return not tokens_without_approval
    return True


def check_amount_unchanged(recorded_amount_minor: int, shown_amount_minor: int) -> None:
    """FR-152: an approved financial request whose amount no longer
    matches what the parent was shown is refused rather than carried out
    at the new figure. No executor supplies `shown_amount_minor` today —
    the two financial kinds ship unregistered (research.md R-46) and
    `approve` raises `approval_kind_not_executable` before this could ever
    run — so this exists as a standalone, directly unit-testable function
    (tests/unit/test_approval_rules.py, T389) ahead of Epic-05's
    executors, exactly as R-46 records."""
    if shown_amount_minor != recorded_amount_minor:
        raise ApprovalAmountChanged("The amount has changed since this request was made.")


class ApprovalService:
    """The Pending Parent Approval workflow's resolution side (US12,
    FR-141 - FR-159). `JoinService` already creates the only requests any
    endpoint raises today (`join_trainer`, Phase C); this service is
    where every one of them is read, decided, answered, and withdrawn,
    plus the one-request-at-a-time expiry the maintenance sweep calls
    into (`expire_one`).

    Every status change goes through `ApprovalRepository.resolve` — the
    single conditional UPDATE whose row count is the decision (research.md
    R-41). No method here reads a request and then writes a status onto
    it separately."""

    def __init__(
        self, db_session: AsyncSession, settings: Settings, email_sender: EmailSender
    ) -> None:
        self._db_session = db_session
        self._settings = settings
        self._email_sender = email_sender
        self._approvals = ApprovalRepository(db_session)
        self._profiles = PlayerProfileRepository(db_session)
        self._users = UserRepository(db_session)
        self._audit = AuditRepository(db_session)

    # --- creation (forward-looking: no endpoint calls this yet — the one
    # request kind any endpoint raises today, `join_trainer`, is created
    # directly by `JoinService._accept_as_child`, which already applies
    # the partial-unique-index check-then-insert convention R-40
    # describes). Kept here, not duplicated, so a future financial-request
    # endpoint (Epic-05) has exactly one place to call. ------------------

    async def create(
        self,
        *,
        player_profile: PlayerProfile,
        parent_user_id: str,
        kind: ApprovalRequestKind,
        trainer_user_id: str | None = None,
        share_link_id: str | None = None,
        amount_minor: int | None = None,
        currency: str | None = None,
    ) -> ApprovalRequest | None:
        """`None` means no approval was needed at all (FR-146's "on"
        setting) — the caller proceeds with the action immediately and
        sends its own informational notice
        (`templates/token_spend_notice.py`); this method never sends
        one itself, since it does not know what "immediately" means for
        a kind it does not execute."""
        if not approval_required(
            kind, tokens_without_approval=player_profile.tokens_without_approval
        ):
            return None

        request = await self._approvals.insert(
            player_profile_id=player_profile.id,
            parent_user_id=parent_user_id,
            kind=kind.value,
            trainer_user_id=trainer_user_id,
            share_link_id=share_link_id,
            amount_minor=amount_minor,
            currency=currency,
        )
        await self._audit.add(
            action="approval_requested",
            actor_user_id=None,
            target_user_id=parent_user_id,
            detail=f"request={request.id} player_profile={player_profile.id} kind={kind.value}",
        )
        return request

    # --- reachability -----------------------------------------------------

    async def _require_parent_owned(self, user_id: str, request_id: str) -> ApprovalRequest:
        """404, not 403, for a request the caller may not reach — another
        account's (research.md R-48, same reasoning FamilyService
        applies)."""
        request = await self._approvals.get_by_id(request_id)
        if request is None or request.parent_user_id != user_id:
            raise NotFound("No such request.")
        return request

    async def _require_child_owned(self, user_id: str, request_id: str) -> ApprovalRequest:
        child_profile = await self._profiles.get_by_sign_in_user_id(user_id)
        if child_profile is None:
            raise NotFound("No such request.")
        request = await self._approvals.get_by_id(request_id)
        if request is None or request.player_profile_id != child_profile.id:
            raise NotFound("No such request.")
        return request

    async def _raiser_profile_ids(self, user_id: str) -> list[str]:
        child_profile = await self._profiles.get_by_sign_in_user_id(user_id)
        if child_profile is not None:
            return [child_profile.id]
        profiles = await self._profiles.list_live_for_account(user_id)
        return [p.id for p in profiles]

    # --- reads (FR-149, FR-153) --------------------------------------------

    async def list_for_parent(
        self,
        user_id: str,
        *,
        status: str | None,
        player_profile_id: str | None,
        page: int,
        page_size: int,
    ) -> ApprovalRequestPage:
        statuses = [status] if status is not None else _LIVE_STATUS_VALUES
        rows, total = await self._approvals.list_for_parent(
            user_id,
            statuses=statuses,
            player_profile_id=player_profile_id,
            page=page,
            page_size=page_size,
        )
        items = [await self._to_out(r) for r in rows]
        return ApprovalRequestPage(items=items, page=page, page_size=page_size, total=total)

    async def get_own_approval(self, user_id: str, request_id: str) -> ApprovalRequestOut:
        request = await self._require_parent_owned(user_id, request_id)
        return await self._to_out(request)

    async def count_pending_for_parent(self, user_id: str) -> int:
        """The navigation frame's badge count (FR-159)."""
        return await self._approvals.count_live_for_parent(user_id)

    async def list_raised_by(
        self, user_id: str, *, status: str | None, page: int, page_size: int
    ) -> ApprovalRequestPage:
        statuses = [status] if status is not None else None
        profile_ids = await self._raiser_profile_ids(user_id)
        rows, total = await self._approvals.list_for_profiles(
            profile_ids, statuses=statuses, page=page, page_size=page_size
        )
        items = [await self._to_out(r) for r in rows]
        return ApprovalRequestPage(items=items, page=page, page_size=page_size, total=total)

    # --- parent decisions (FR-150, FR-156, FR-157, FR-158) -----------------

    async def approve(
        self, user_id: str, request_id: str, *, note: str | None
    ) -> ApprovalRequestOut:
        """FR-142, FR-144, FR-151, FR-152, R-42: the status flip and the
        executor run inside one SAVEPOINT. A domain error from the
        executor rolls both back, leaving the request exactly as live as
        it was; an unregistered kind is refused before either write is
        attempted (FR-142, R-46)."""
        request = await self._require_parent_owned(user_id, request_id)
        kind = ApprovalRequestKind(request.kind)
        executor = get_executor(kind)
        if executor is None:
            raise ApprovalKindNotExecutable("This kind of request cannot be completed yet.")

        async with self._db_session.begin_nested():
            rowcount = await self._approvals.resolve(
                request_id=request.id,
                target_status=ApprovalRequestStatus.APPROVED.value,
                resolved_by_user_id=user_id,
                from_statuses=[ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value],
                parent_note=note,
                require_active_parent=True,
            )
            if rowcount == 0:
                raise RequestAlreadyResolved("This request has already been decided.")
            await executor.execute(request, db_session=self._db_session)

        resolved = await self._approvals.get_by_id(request.id)
        assert resolved is not None
        await self._audit_decision(resolved, action="approval_approved", actor_user_id=user_id)
        await self._notify_decision(resolved, decision="approved")
        return await self._to_out(resolved)

    async def deny(self, user_id: str, request_id: str, *, note: str | None) -> ApprovalRequestOut:
        request = await self._require_parent_owned(user_id, request_id)
        rowcount = await self._approvals.resolve(
            request_id=request.id,
            target_status=ApprovalRequestStatus.DENIED.value,
            resolved_by_user_id=user_id,
            from_statuses=[
                ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value,
                ApprovalRequestStatus.INFO_REQUESTED.value,
            ],
            parent_note=note,
            require_active_parent=True,
        )
        if rowcount == 0:
            raise RequestAlreadyResolved("This request has already been decided.")

        resolved = await self._approvals.get_by_id(request.id)
        assert resolved is not None
        await self._audit_decision(resolved, action="approval_denied", actor_user_id=user_id)
        await self._notify_decision(resolved, decision="denied")
        return await self._to_out(resolved)

    async def request_info(self, user_id: str, request_id: str, *, note: str) -> ApprovalRequestOut:
        """Moves to `info_requested`, a live status — `expires_at` is
        never touched (FR-155's last sentence, research.md R-43)."""
        request = await self._require_parent_owned(user_id, request_id)
        rowcount = await self._approvals.resolve(
            request_id=request.id,
            target_status=ApprovalRequestStatus.INFO_REQUESTED.value,
            resolved_by_user_id=None,
            from_statuses=[ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value],
            parent_note=note,
            require_active_parent=True,
        )
        if rowcount == 0:
            raise RequestAlreadyResolved("This request has already been decided.")

        resolved = await self._approvals.get_by_id(request.id)
        assert resolved is not None
        await self._audit_decision(
            resolved, action="approval_info_requested", actor_user_id=user_id
        )
        await self._notify_decision(resolved, decision="info_requested")
        return await self._to_out(resolved)

    # --- child actions (FR-143, FR-153, FR-154, FR-156) --------------------

    async def withdraw(self, user_id: str, request_id: str) -> ApprovalRequestOut:
        request = await self._require_child_owned(user_id, request_id)
        rowcount = await self._approvals.resolve(
            request_id=request.id,
            target_status=ApprovalRequestStatus.WITHDRAWN.value,
            resolved_by_user_id=user_id,
            from_statuses=[
                ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value,
                ApprovalRequestStatus.INFO_REQUESTED.value,
            ],
            require_active_parent=True,
        )
        if rowcount == 0:
            raise RequestAlreadyResolved("This request has already been decided.")

        resolved = await self._approvals.get_by_id(request.id)
        assert resolved is not None
        await self._audit_decision(resolved, action="approval_withdrawn", actor_user_id=user_id)
        return await self._to_out(resolved)

    async def respond(self, user_id: str, request_id: str, *, note: str) -> ApprovalRequestOut:
        """Only from `info_requested`, back to `pending_parent_approval` —
        still live, so `expires_at` is untouched (FR-143, FR-155)."""
        request = await self._require_child_owned(user_id, request_id)
        rowcount = await self._approvals.resolve(
            request_id=request.id,
            target_status=ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value,
            resolved_by_user_id=None,
            from_statuses=[ApprovalRequestStatus.INFO_REQUESTED.value],
            child_note=note,
            require_active_parent=True,
        )
        if rowcount == 0:
            raise RequestAlreadyResolved("This request is not awaiting information.")

        resolved = await self._approvals.get_by_id(request.id)
        assert resolved is not None
        await self._audit_decision(resolved, action="approval_responded", actor_user_id=user_id)
        return await self._to_out(resolved)

    # --- expiry (FR-155, research.md R-43) ---------------------------------

    async def expire_one(self, request: ApprovalRequest, *, now: datetime) -> bool:
        """Materializes `expired` for one lapsed row and sends both
        notifications. Called once per candidate by
        `MaintenanceService.expire_lapsed_approval_requests`
        (`ApprovalRepository.list_lapsed_live` supplies the candidates);
        never carries `require_active_parent`, because a request must
        expire on schedule even when the parent has left Active status
        (FR-157's last clause) — only a *person's* resolution is refused
        by that guard, not the sweep's. Returns `False` when another
        caller (a decision, or a second sweep run) already resolved it
        first — the same race R-41 protects everywhere else, guarded here
        rather than assumed."""
        rowcount = await self._approvals.resolve(
            request_id=request.id,
            target_status=ApprovalRequestStatus.EXPIRED.value,
            resolved_by_user_id=None,
            from_statuses=[
                ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value,
                ApprovalRequestStatus.INFO_REQUESTED.value,
            ],
            now=now,
            require_lapsed=True,
        )
        if rowcount == 0:
            return False

        resolved = await self._approvals.get_by_id(request.id)
        assert resolved is not None
        await self._audit_decision(resolved, action="approval_expired", actor_user_id=None)
        await self._notify_expiry(resolved)
        return True

    # --- audit (FR-158) -----------------------------------------------------

    async def _audit_decision(
        self, request: ApprovalRequest, *, action: str, actor_user_id: str | None
    ) -> None:
        """`target_user_id` names the parent account, since `audit_entries.
        target_user_id` is a foreign key into `users` and a player profile
        has no row there (data-model.md §8) — the child profile the
        decision concerns is instead named in `detail`, alongside the
        request, the note if any, and the kind. `actor_user_id=None` for
        an expiry, matching `ck_approval_requests_expiry_actor`'s own rule
        that it is the one resolution nobody performed."""
        detail = (
            f"request={request.id} player_profile={request.player_profile_id} kind={request.kind}"
        )
        if request.parent_note:
            detail += f" parent_note={request.parent_note!r}"
        if request.child_note:
            detail += f" child_note={request.child_note!r}"
        await self._audit.add(
            action=action,
            actor_user_id=actor_user_id,
            target_user_id=request.parent_user_id,
            detail=detail,
        )

    # --- notifications (FR-148, FR-153, FR-155, research.md R-51) ----------

    async def _describe_subject(self, request: ApprovalRequest) -> str:
        if request.kind == ApprovalRequestKind.JOIN_TRAINER.value and request.trainer_user_id:
            trainer = await self._users.get_by_id(request.trainer_user_id)
            name = ""
            if trainer is not None:
                trainer_org = await self._users.get_role_detail(trainer)
                name = (
                    trainer_org.business_name
                    if isinstance(trainer_org, TrainerOrganization)
                    else ""
                )
            return f"join {name}".strip()
        return "make this request"

    async def _display_name(self, player_profile: PlayerProfile) -> str:
        if player_profile.kind == PlayerProfileKind.CHILD.value:
            return f"{player_profile.first_name} {player_profile.last_name}"
        account_profile = await self._users.get_profile(player_profile.account_user_id)
        assert account_profile is not None
        return f"{account_profile.first_name} {account_profile.last_name}"

    async def _notify_decision(self, request: ApprovalRequest, *, decision: str) -> None:
        """Addressed to the **child** — the exception T395/R-51 carve out
        of "every notification goes to the parent": this is the child's
        own status notice (FR-153). Silently skipped when the profile has
        no sign-in to notify, e.g. a parent revoked it while the request
        waited."""
        player_profile = await self._profiles.get_by_id(request.player_profile_id)
        if player_profile is None or player_profile.sign_in_user_id is None:
            return
        child_user = await self._users.get_by_id(player_profile.sign_in_user_id)
        if child_user is None:
            return

        what_was_asked = await self._describe_subject(request)
        child_display_name = await self._display_name(player_profile)
        subject, body = render_approval_decided_email(
            child_display_name=child_display_name,
            decision=decision,
            what_was_asked=what_was_asked,
            parent_note=request.parent_note,
        )
        await self._email_sender.send(to=child_user.email, subject=subject, body=body)

    async def _notify_expiry(self, request: ApprovalRequest) -> None:
        """FR-155: both the parent and the child (research.md R-43's
        "the sweep notifies")."""
        what_was_asked = await self._describe_subject(request)
        player_profile = await self._profiles.get_by_id(request.player_profile_id)
        child_display_name = (
            await self._display_name(player_profile) if player_profile is not None else "Your child"
        )

        parent = await self._users.get_by_id(request.parent_user_id)
        if parent is not None:
            subject, body = render_approval_expired_email_to_parent(
                child_display_name=child_display_name, what_was_asked=what_was_asked
            )
            await self._email_sender.send(to=parent.email, subject=subject, body=body)

        if player_profile is not None and player_profile.sign_in_user_id is not None:
            child_user = await self._users.get_by_id(player_profile.sign_in_user_id)
            if child_user is not None:
                subject, body = render_approval_expired_email_to_child(
                    what_was_asked=what_was_asked
                )
                await self._email_sender.send(to=child_user.email, subject=subject, body=body)

    # --- serialization -------------------------------------------------------

    async def _to_out(self, request: ApprovalRequest) -> ApprovalRequestOut:
        player_profile = await self._profiles.get_by_id(request.player_profile_id)
        assert player_profile is not None
        player_display_name = await self._display_name(player_profile)

        trainer_display_name: str | None = None
        if request.trainer_user_id is not None:
            trainer = await self._users.get_by_id(request.trainer_user_id)
            if trainer is not None:
                trainer_org = await self._users.get_role_detail(trainer)
                trainer_display_name = (
                    trainer_org.business_name
                    if isinstance(trainer_org, TrainerOrganization)
                    else ""
                )

        resolved_by: str | None = None
        if request.resolved_by_user_id is not None:
            if request.resolved_by_user_id == request.parent_user_id:
                resolved_by = "parent"
            elif request.resolved_by_user_id == player_profile.sign_in_user_id:
                resolved_by = "child"
            else:
                resolved_by = "super_admin"

        return ApprovalRequestOut(
            id=request.id,
            player_profile_id=request.player_profile_id,
            player_display_name=player_display_name,
            kind=ApprovalRequestKind(request.kind),
            status=ApprovalRequestStatus(request.status),
            trainer_id=request.trainer_user_id,
            trainer_display_name=trainer_display_name,
            amount_minor=request.amount_minor,
            currency=request.currency,
            requested_at=request.requested_at,
            expires_at=request.expires_at,
            parent_note=request.parent_note,
            child_note=request.child_note,
            resolved_at=request.resolved_at,
            resolved_by=resolved_by,
        )
