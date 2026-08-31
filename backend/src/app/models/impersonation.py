from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid, utcnow
from app.models.enums import AccountStatus, ImpersonationEndReason

_STATUS_AT_START_VALUES = ", ".join(
    f"'{s.value}'" for s in (AccountStatus.ACTIVE, AccountStatus.INACTIVE)
)
_END_REASON_VALUES = ", ".join(f"'{r.value}'" for r in ImpersonationEndReason)


class ImpersonationSession(Base):
    """One occasion on which a Super Admin viewed the platform as another
    person (data-model.md §105, FR-040 – FR-056). Append-only and
    trigger-protected, the same shape as `audit_entries` (revision 0004):
    the repository this feature adds exposes insert / close / select
    only, and revision 0011 installs
    `trg_impersonation_sessions_no_delete` and
    `trg_impersonation_sessions_no_update_closed` as defence in depth
    against a script that bypasses the repository.

    `auth_session_id` deliberately carries **no** foreign key to
    `sessions`: a session row is deletable and short-lived (`ON DELETE
    CASCADE` from `users`), while this row must outlive both the session
    it rode on and the erasure of the account it names (research.md
    R2-18). The same reasoning already governs `SignInAttempt`
    (`app.models.auth`), which has no FK to `users` for the identical
    reason. This column is a breadcrumb for support, never joined by any
    query this feature writes.

    Duration is not stored — it is `ended_at - started_at`, computed in
    the response schema, so two columns in one row cannot come to
    disagree.
    """

    __tablename__ = "impersonation_sessions"
    __table_args__ = (
        CheckConstraint(
            "(ended_at IS NULL) = (end_reason IS NULL)",
            name="ck_impersonation_sessions_end_pair",
        ),
        CheckConstraint(
            f"end_reason IS NULL OR end_reason IN ({_END_REASON_VALUES})",
            name="ck_impersonation_sessions_end_reason",
        ),
        CheckConstraint(
            f"target_status_at_start IN ({_STATUS_AT_START_VALUES})",
            name="ck_impersonation_sessions_status_at_start",
        ),
        CheckConstraint(
            "admin_user_id <> target_user_id", name="ck_impersonation_sessions_not_self"
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_impersonation_sessions_order",
        ),
        Index("ix_impersonation_sessions_admin", "admin_user_id", "started_at"),
        Index("ix_impersonation_sessions_target", "target_user_id", "started_at"),
        Index(
            "ix_impersonation_sessions_open",
            "admin_user_id",
            sqlite_where=text("ended_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    admin_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    target_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    # No ForeignKey — see class docstring and research.md R2-18.
    auth_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    target_status_at_start: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String, nullable=True)
