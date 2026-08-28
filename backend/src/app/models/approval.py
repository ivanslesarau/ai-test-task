from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid, utcnow
from app.models.enums import (
    LIVE_APPROVAL_STATUSES,
    ApprovalRequestKind,
    ApprovalRequestStatus,
)

_KIND_VALUES = ", ".join(f"'{k.value}'" for k in ApprovalRequestKind)
_STATUS_VALUES = ", ".join(f"'{s.value}'" for s in ApprovalRequestStatus)
_LIVE_VALUES = ", ".join(f"'{s.value}'" for s in sorted(LIVE_APPROVAL_STATUSES))
_TERMINAL_VALUES = ", ".join(
    f"'{s.value}'" for s in ApprovalRequestStatus if s not in LIVE_APPROVAL_STATUSES
)
_FINANCIAL_VALUES = ", ".join(
    f"'{k.value}'" for k in (ApprovalRequestKind.USD_PAYMENT, ApprovalRequestKind.TOKEN_SPEND)
)

# 48 hours, as FR-155 states. Written into expires_at once at creation and
# never recomputed, so a return from INFO_REQUESTED to pending cannot
# restart the clock — there is no clock, only a timestamp nobody rewrites
# (research.md R-43).
APPROVAL_REQUEST_TTL_HOURS = 48


class ApprovalRequest(Base):
    """One thing a child asked for and a parent must decide
    (data-model.md §28, FR-141 – FR-159).

    One table with a `kind` discriminator, because Epic-01 describes the
    same wait-for-the-parent behaviour three times over — a USD payment, a
    token spend, and a child asking to join a trainer. The subject is
    expressed as **typed nullable columns with check constraints**, never a
    JSON payload: Principle II exists to keep untyped dicts out of a
    multi-role permission system, and a JSON `{"trainer_id": ...}` carries
    no foreign key, so nothing would stop a request naming a trainer that
    no longer exists (research.md R-39).

    Two guarantees live in this table's indexes rather than in service
    code:

    * `uq_approval_requests_live` makes "at most one live request per child
      and subject" true by construction (FR-139, research.md R-40). It is
      **partial** so that a denied request does not bar the child from ever
      asking again.
    * `(status, expires_at)` is the sweep's only query and must be an index
      scan (research.md R-43).

    Resolution never reads then writes. `ApprovalRepository` issues one
    conditional UPDATE whose row count *is* the decision, which is what
    makes FR-156's resolve-exactly-once and the expiry race a single
    predicate rather than a lock (research.md R-41).
    """

    __tablename__ = "approval_requests"
    __table_args__ = (
        CheckConstraint(f"kind IN ({_KIND_VALUES})", name="ck_approval_requests_kind"),
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="ck_approval_requests_status"),
        # The subject matches the kind, at the schema level. This is the
        # guarantee a JSON payload could not give.
        CheckConstraint(
            "("
            f"kind = '{ApprovalRequestKind.JOIN_TRAINER.value}'"
            " AND trainer_user_id IS NOT NULL"
            " AND amount_minor IS NULL AND currency IS NULL"
            ") OR ("
            f"kind IN ({_FINANCIAL_VALUES})"
            " AND amount_minor IS NOT NULL AND currency IS NOT NULL"
            " AND trainer_user_id IS NULL"
            ")",
            name="ck_approval_requests_subject",
        ),
        # A resolved request always says when; a live one never does.
        CheckConstraint(
            f"(status IN ({_LIVE_VALUES}) AND resolved_at IS NULL)"
            f" OR (status IN ({_TERMINAL_VALUES}) AND resolved_at IS NOT NULL)",
            name="ck_approval_requests_resolution",
        ),
        # Expiry is the one resolution with no actor. Recording a spurious
        # one would misattribute a decision nobody took.
        CheckConstraint(
            f"status <> '{ApprovalRequestStatus.EXPIRED.value}' OR resolved_by_user_id IS NULL",
            name="ck_approval_requests_expiry_actor",
        ),
        Index(
            "uq_approval_requests_live",
            "player_profile_id",
            "kind",
            "trainer_user_id",
            unique=True,
            sqlite_where=text(f"status IN ({_LIVE_VALUES})"),
        ),
        Index("ix_approval_requests_parent_status", "parent_user_id", "status"),
        Index("ix_approval_requests_profile_status", "player_profile_id", "status"),
        Index("ix_approval_requests_status_expiry", "status", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    player_profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("player_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Recorded here rather than reached through the profile, so the
    # responsible adult at the time of the request is fixed.
    parent_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value,
    )

    # Subject of a JOIN_TRAINER request.
    trainer_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    share_link_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("share_links.id"), nullable=True
    )

    # Minor currency units — an integer, never a float. Money in a binary
    # float is a defect waiting for its first rounding (research.md R-39).
    # This is the amount **as shown to the parent**: approving at a
    # different figure is refused rather than charged (FR-152).
    amount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    requested_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)

    parent_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    child_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # The parent, the child (for a withdrawal), or NULL for an expiry,
    # which no one performed.
    resolved_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
