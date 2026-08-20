from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid, utcnow


class AuditEntry(Base):
    """Append-only record of every administrative action
    (data-model.md §8, FR-054, FR-055, R-16).

    The repository for this table exposes insert and select only. An
    Alembic revision additionally installs SQLite triggers that raise on
    UPDATE/DELETE against this table, so the guarantee survives a future
    script that bypasses the repository.
    """

    __tablename__ = "audit_entries"
    __table_args__ = (
        Index("ix_audit_entries_target", "target_user_id"),
        Index("ix_audit_entries_action", "action"),
        Index("ix_audit_entries_occurred_at", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    target_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)


class ErasureRecord(Base):
    """The legally retained trace of one privacy erasure
    (data-model.md §9, FR-049, R-08). Reachable through exactly one
    Super-Admin-only endpoint; never joined into any account view.
    """

    __tablename__ = "erasure_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, unique=True
    )
    original_email: Mapped[str] = mapped_column(String(320), nullable=False)
    original_first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    original_last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    erased_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    erased_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
