from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid, utcnow
from app.models.enums import CoachInvitationBlockReason, CoachInvitationState

_STATE_VALUES = ", ".join(f"'{s.value}'" for s in CoachInvitationState)
_BLOCK_REASON_VALUES = ", ".join(f"'{r.value}'" for r in CoachInvitationBlockReason)


class CoachInvitation(Base):
    """One trainer's offer to one address to become a coach on their
    roster (data-model.md §101, FR-001 – FR-019). A dedicated table
    rather than a `share_links` kind — research.md R2-01 records the four
    reasons: the opposite security posture of the secret, the five
    columns that would sit permanently NULL on every player row, the
    differing lifecycles, and the differing (here disclosing, there
    uniform) refusal messages.

    `token_hash` is a SHA-256 of the mailed token — the raw token exists
    only in the emailed URL, mirroring `CredentialSetupInvitation`
    (research.md R2-02).

    `state` stores only the four event-driven values; `expired` is
    derived at read time from `expires_at`, and `blocked` is not a state
    at all — it is the nullable `blocked_at`/`blocked_reason` pair on a
    row that stays `awaiting`, so FR-015's refusal does not spend the
    invitation (§101.1, §101.2, research.md R2-03).

    Deliberately no unique index on `(trainer_user_id, invited_email)`:
    a trainer may hold several rows for one address over time (one
    accepted, one superseded, one revoked). FR-007's narrower rule — no
    second row that is presently awaiting-and-unexpired — is enforced in
    `CoachInvitationService.issue`, which is also where the 409 body
    naming the existing invitation is built (§101).
    """

    __tablename__ = "coach_invitations"
    __table_args__ = (
        CheckConstraint(f"state IN ({_STATE_VALUES})", name="ck_coach_invitations_state"),
        CheckConstraint(
            f"blocked_reason IS NULL OR blocked_reason IN ({_BLOCK_REASON_VALUES})",
            name="ck_coach_invitations_block_reason",
        ),
        CheckConstraint(
            "(blocked_at IS NULL) = (blocked_reason IS NULL)",
            name="ck_coach_invitations_blocked_pair",
        ),
        CheckConstraint(
            "(accepted_at IS NULL) = (accepted_by_user_id IS NULL)",
            name="ck_coach_invitations_accepted_pair",
        ),
        CheckConstraint(
            "state <> 'accepted' OR accepted_at IS NOT NULL",
            name="ck_coach_invitations_terminal_pair",
        ),
        Index("ix_coach_invitations_trainer_state", "trainer_user_id", "state"),
        Index("uq_coach_invitations_token_hash", "token_hash", unique=True),
        Index("ix_coach_invitations_trainer_email", "trainer_user_id", "invited_email"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    trainer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    invited_email: Mapped[str] = mapped_column(String(320), nullable=False)
    invitee_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    accepted_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("coach_invitations.id"), nullable=True
    )
    blocked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(String, nullable=True)
