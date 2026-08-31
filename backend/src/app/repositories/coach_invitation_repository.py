from datetime import datetime
from typing import cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid, utcnow
from app.models.coach_invitation import CoachInvitation
from app.models.enums import CoachInvitationBlockReason, CoachInvitationState


class CoachInvitationRepository:
    """Queries only — the presented-state derivation and every business
    rule live in `CoachInvitationService` (data-model.md §101.1, §101.2),
    mirroring the split `ShareLinkRepository`/`ShareLinkService` and
    `InvitationRepository`/`UserAdminService` already establish."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        trainer_user_id: str,
        created_by_user_id: str,
        token_hash: str,
        invited_email: str,
        invitee_name: str | None,
        message: str | None,
        expires_at: datetime,
    ) -> CoachInvitation:
        invitation = CoachInvitation(
            id=new_uuid(),
            trainer_user_id=trainer_user_id,
            created_by_user_id=created_by_user_id,
            token_hash=token_hash,
            invited_email=invited_email,
            invitee_name=invitee_name,
            message=message,
            state=CoachInvitationState.AWAITING.value,
            issued_at=utcnow(),
            expires_at=expires_at,
            accepted_by_user_id=None,
            accepted_at=None,
            revoked_at=None,
            superseded_at=None,
            superseded_by_id=None,
            blocked_at=None,
            blocked_reason=None,
        )
        self._session.add(invitation)
        await self._session.flush()
        return invitation

    async def get_by_id(self, invitation_id: str) -> CoachInvitation | None:
        return await self._session.get(CoachInvitation, invitation_id)

    async def get_by_token_hash(self, token_hash: str) -> CoachInvitation | None:
        """Unused by User Story 1's own endpoints — reserved for US2's
        preview/register/accept, which resolve a raw mailed token to a
        row (tasks.md T551, research.md R2-05). Kept here rather than
        added later so this repository needs no shape change when US2
        extends the service that calls it."""
        result = await self._session.execute(
            select(CoachInvitation).where(CoachInvitation.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def list_for_trainer(self, trainer_user_id: str) -> list[CoachInvitation]:
        """Every non-superseded row for this trainer, newest first — a
        resend leaves exactly one row per address in this list (FR-005).

        Deliberately returns the full (small, trainer-scoped) set rather
        than a `LIMIT`/`OFFSET` page: the `expired`/`blocked` values a
        caller may filter or paginate by are read-time derivations, not
        columns a `WHERE` clause can express (data-model.md §101.1), so
        `CoachInvitationService.list_for_trainer` filters and paginates
        the already-derived list instead."""
        result = await self._session.execute(
            select(CoachInvitation)
            .where(
                CoachInvitation.trainer_user_id == trainer_user_id,
                CoachInvitation.state != CoachInvitationState.SUPERSEDED.value,
            )
            .order_by(CoachInvitation.issued_at.desc())
        )
        return list(result.scalars().all())

    async def find_live_for_email(
        self, trainer_user_id: str, invited_email: str
    ) -> CoachInvitation | None:
        """FR-007's duplicate guard: the row, if any, that is presently
        `awaiting` and unexpired for this `(trainer, address)` pair —
        `is_usable`'s predicate (§101.2) without the `blocked_at`
        exemption, since a blocked row is `awaiting` by construction and
        so is already covered by the `state` filter here. Backed by
        `ix_coach_invitations_trainer_email`."""
        result = await self._session.execute(
            select(CoachInvitation).where(
                CoachInvitation.trainer_user_id == trainer_user_id,
                CoachInvitation.invited_email == invited_email,
                CoachInvitation.state == CoachInvitationState.AWAITING.value,
                CoachInvitation.expires_at > utcnow(),
            )
        )
        return result.scalar_one_or_none()

    async def mark_revoked(self, invitation: CoachInvitation) -> None:
        invitation.state = CoachInvitationState.REVOKED.value
        invitation.revoked_at = utcnow()
        await self._session.flush()

    async def mark_superseded(self, invitation: CoachInvitation, *, superseded_by_id: str) -> None:
        invitation.state = CoachInvitationState.SUPERSEDED.value
        invitation.superseded_at = utcnow()
        invitation.superseded_by_id = superseded_by_id
        await self._session.flush()

    async def mark_accepted(self, invitation_id: str, *, accepted_by_user_id: str) -> int:
        """The FR-018 conditional UPDATE: two concurrent acceptances of
        the same invitation resolve to exactly one winner, with no read-
        then-write race (data-model.md §111.1, mirroring
        `ApprovalRepository.resolve`). The WHERE clause — `state =
        'awaiting'` and unexpired — is the whole guard; a second call
        against the same row, or one racing this one, matches zero rows
        rather than needing a lock. Returns the row count: `1` means this
        call won, `0` means the invitation was no longer awaiting-and-
        unexpired by the time this ran (already accepted concurrently, or
        it expired in the gap since the caller last checked)."""
        result = cast(
            CursorResult,
            await self._session.execute(
                update(CoachInvitation)
                .where(
                    CoachInvitation.id == invitation_id,
                    CoachInvitation.state == CoachInvitationState.AWAITING.value,
                    CoachInvitation.expires_at > utcnow(),
                )
                .values(
                    state=CoachInvitationState.ACCEPTED.value,
                    accepted_by_user_id=accepted_by_user_id,
                    accepted_at=utcnow(),
                )
            ),
        )
        await self._session.flush()
        return result.rowcount or 0

    async def set_block(
        self, invitation: CoachInvitation, *, reason: CoachInvitationBlockReason
    ) -> None:
        """FR-014/FR-015: a refused acceptance annotates the row rather
        than spending it (data-model.md §101.1, §101.2, research.md
        R2-03) — `state` is untouched, so the invitation stays usable."""
        invitation.blocked_at = utcnow()
        invitation.blocked_reason = reason.value
        await self._session.flush()

    async def clear_block(self, invitation: CoachInvitation) -> None:
        """Cleared on a later successful acceptance (FR-019)."""
        invitation.blocked_at = None
        invitation.blocked_reason = None
        await self._session.flush()

    @staticmethod
    def is_usable(invitation: CoachInvitation, *, now: datetime | None = None) -> bool:
        """data-model.md §101.2. `blocked_at` deliberately plays no part:
        FR-015 requires that a refused acceptance not spend the
        invitation, so a blocked row stays usable until it expires or is
        revoked or resent."""
        now = now or utcnow()
        return (
            invitation.state == CoachInvitationState.AWAITING.value and invitation.expires_at > now
        )
