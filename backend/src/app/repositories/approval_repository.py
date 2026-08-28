from datetime import datetime, timedelta
from typing import cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid, utcnow
from app.models.approval import APPROVAL_REQUEST_TTL_HOURS, ApprovalRequest
from app.models.enums import LIVE_APPROVAL_STATUSES, AccountStatus, ApprovalRequestStatus
from app.models.user import User

_LIVE_VALUES = [s.value for s in LIVE_APPROVAL_STATUSES]


class ApprovalRepository:
    """Queries only (data-model.md §28, T322). The one exception to
    "queries only" is `resolve` — a Core `update()` whose row count *is*
    the decision (research.md R-41), which is what keeps resolution free
    of a read-then-write race. No method here reads a row and then writes
    it back for a status change; every status change goes through
    `resolve`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        player_profile_id: str,
        parent_user_id: str,
        kind: str,
        trainer_user_id: str | None = None,
        share_link_id: str | None = None,
        amount_minor: int | None = None,
        currency: str | None = None,
    ) -> ApprovalRequest:
        """Raises sqlalchemy.exc.IntegrityError on the partial unique
        index `uq_approval_requests_live` when a live request already
        exists for this (player_profile_id, kind, trainer_user_id) —
        the caller follows this codebase's check-then-insert convention
        (research.md R-40)."""
        now = utcnow()
        record = ApprovalRequest(
            id=new_uuid(),
            player_profile_id=player_profile_id,
            parent_user_id=parent_user_id,
            kind=kind,
            status=ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value,
            trainer_user_id=trainer_user_id,
            share_link_id=share_link_id,
            amount_minor=amount_minor,
            currency=currency,
            requested_at=now,
            expires_at=now + timedelta(hours=APPROVAL_REQUEST_TTL_HOURS),
            parent_note=None,
            child_note=None,
            resolved_at=None,
            resolved_by_user_id=None,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_by_id(self, request_id: str) -> ApprovalRequest | None:
        return await self._session.get(ApprovalRequest, request_id)

    async def get_live_for_subject(
        self, *, player_profile_id: str, kind: str, trainer_user_id: str | None
    ) -> ApprovalRequest | None:
        """The row `insert`'s IntegrityError points at — fetched
        separately so the service can return "here is the one already
        waiting" rather than merely refusing (research.md R-40)."""
        result = await self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.player_profile_id == player_profile_id,
                ApprovalRequest.kind == kind,
                ApprovalRequest.trainer_user_id == trainer_user_id,
                ApprovalRequest.status.in_(_LIVE_VALUES),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_parent(
        self,
        parent_user_id: str,
        *,
        statuses: list[str] | None,
        player_profile_id: str | None = None,
        page: int,
        page_size: int,
    ) -> tuple[list[ApprovalRequest], int]:
        """The parent's decision queue (FR-149, index `(parent_user_id,
        status)`). `statuses=None` means every status; the service passes
        the live pair by default, because this is a queue, not a history
        (contract `GET /me/approvals`). `player_profile_id` narrows to one
        child — safe to trust unvalidated here because it is ANDed with
        `parent_user_id`, so a profile on another account simply matches
        nothing rather than leaking (research.md R-48)."""
        base = select(ApprovalRequest).where(ApprovalRequest.parent_user_id == parent_user_id)
        if statuses is not None:
            base = base.where(ApprovalRequest.status.in_(statuses))
        if player_profile_id is not None:
            base = base.where(ApprovalRequest.player_profile_id == player_profile_id)

        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()

        rows = await self._session.execute(
            base.order_by(ApprovalRequest.expires_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows.scalars().all()), total

    async def count_live_for_parent(self, parent_user_id: str) -> int:
        """The navigation frame's pending count (FR-159) — live statuses
        only, no page fetched."""
        result = await self._session.execute(
            select(func.count()).where(
                ApprovalRequest.parent_user_id == parent_user_id,
                ApprovalRequest.status.in_(_LIVE_VALUES),
            )
        )
        return result.scalar_one()

    async def list_for_profiles(
        self,
        player_profile_ids: list[str],
        *,
        statuses: list[str] | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ApprovalRequest], int]:
        """The child's own view of what they asked for (FR-153, index
        `(player_profile_id, status)`). Takes a list because a parent
        calling the same endpoint (`GET /me/requests`) is scoped to every
        profile their own account raises requests through, normally none
        (contract's `listOwnRaisedRequests`)."""
        if not player_profile_ids:
            return [], 0

        base = select(ApprovalRequest).where(
            ApprovalRequest.player_profile_id.in_(player_profile_ids)
        )
        if statuses is not None:
            base = base.where(ApprovalRequest.status.in_(statuses))

        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()

        rows = await self._session.execute(
            base.order_by(ApprovalRequest.requested_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows.scalars().all()), total

    async def list_lapsed_live(self, *, now: datetime | None = None) -> list[ApprovalRequest]:
        """The maintenance sweep's only query (research.md R-43) — must
        stay an index scan against `(status, expires_at)`."""
        now = now or utcnow()
        result = await self._session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.status.in_(_LIVE_VALUES),
                ApprovalRequest.expires_at <= now,
            )
        )
        return list(result.scalars().all())

    async def expire_all_live_for_parent(
        self, parent_user_id: str, *, now: datetime | None = None
    ) -> int:
        """Erasure's cascade (data-model.md §30): every live request tied
        to an erased family is expired, `resolved_by_user_id` left NULL
        because no one performed this — the same "no actor" rule
        `ck_approval_requests_expiry_actor` gives a natural expiry — and
        both free-text notes cleared, since they may name someone. Unlike
        `resolve`, this is a deliberate bulk write scoped to one parent's
        own requests, not a race-sensitive single-row decision."""
        now = now or utcnow()
        result = cast(
            CursorResult,
            await self._session.execute(
                update(ApprovalRequest)
                .where(
                    ApprovalRequest.parent_user_id == parent_user_id,
                    ApprovalRequest.status.in_(_LIVE_VALUES),
                )
                .values(
                    status=ApprovalRequestStatus.EXPIRED.value,
                    resolved_at=now,
                    resolved_by_user_id=None,
                    parent_note=None,
                    child_note=None,
                )
            ),
        )
        await self._session.flush()
        return result.rowcount or 0

    async def resolve(
        self,
        *,
        request_id: str,
        target_status: str,
        resolved_by_user_id: str | None,
        from_statuses: list[str] | None = None,
        parent_note: str | None = None,
        child_note: str | None = None,
        now: datetime | None = None,
        require_active_parent: bool = False,
        require_lapsed: bool = False,
    ) -> int:
        """One conditional UPDATE whose row count *is* the decision
        (research.md R-41): the WHERE clause carries the id, the source
        statuses this specific transition is legal from, and an
        `expires_at` comparison, so a second resolution attempt, a
        resolution racing the sweep, a resolution racing expiry, and an
        attempt at a transition FR-143 does not permit (e.g. approving
        straight out of `info_requested`) all match zero rows rather than
        requiring a lock or a second check. Returns the number of rows
        affected — 1 means this call resolved it, 0 means it was already
        resolved, withdrawn, had already lapsed, or was not in a status
        this transition starts from.

        `require_lapsed=False` (the default, every person-driven decision)
        requires `expires_at > now` — a request past its deadline cannot
        be approved, denied, asked about, withdrawn, or responded to, even
        if the sweep has not yet run (research.md R-41's "expiry racing a
        decision"). `require_lapsed=True` — the maintenance sweep's own
        call — flips that to `expires_at <= now`: the complementary half
        of the same predicate, matching exactly the rows a person's
        decision would refuse and nothing a person could still resolve, so
        the two paths can never both take effect on one row.

        `from_statuses` defaults to both live statuses — the caller names
        a narrower set (data-model.md §25's `ALLOWED_APPROVAL_TRANSITIONS`)
        whenever the target is reachable from only one of them.

        `target_status` itself being live (`info_requested`, or
        `pending_parent_approval` for a child's reply) leaves
        `resolved_at`/`resolved_by_user_id` `NULL` — `ck_approval_requests_
        resolution` requires exactly that pairing, and it is what makes
        FR-155's "asking a question does not restart the clock" free: no
        column here ever touches `expires_at`.

        `require_active_parent=True` adds one more clause to the same
        WHERE — the parent's account must be Active — which is FR-157
        enforced as part of the same predicate rather than a separate
        check (research.md R-41). The expiry sweep
        (`maintenance_service.expire_lapsed_approval_requests`)
        deliberately leaves this at its default `False`: a request tied to
        a now-inactive parent must still expire on its original schedule
        (FR-157's last clause), only its *resolution* by a person is
        refused."""
        now = now or utcnow()
        is_terminal_target = target_status not in _LIVE_VALUES
        values: dict[str, object] = {
            "status": target_status,
            "resolved_at": now if is_terminal_target else None,
            "resolved_by_user_id": resolved_by_user_id if is_terminal_target else None,
        }
        if parent_note is not None:
            values["parent_note"] = parent_note
        if child_note is not None:
            values["child_note"] = child_note

        allowed_statuses = from_statuses if from_statuses is not None else _LIVE_VALUES
        expiry_condition = (
            ApprovalRequest.expires_at <= now
            if require_lapsed
            else ApprovalRequest.expires_at > now
        )
        conditions = [
            ApprovalRequest.id == request_id,
            ApprovalRequest.status.in_(allowed_statuses),
            expiry_condition,
        ]
        if require_active_parent:
            conditions.append(
                ApprovalRequest.parent_user_id.in_(
                    select(User.id).where(User.status == AccountStatus.ACTIVE.value)
                )
            )

        result = cast(
            CursorResult,
            await self._session.execute(
                update(ApprovalRequest).where(*conditions).values(**values)
            ),
        )
        await self._session.flush()
        return result.rowcount or 0
