from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid, utcnow


class Session(Base):
    """An admitted person's continuing access (data-model.md §5, R-03).

    Only `token_hash` is stored — the raw token exists only in the cookie,
    so a leaked database yields no usable session.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # The open impersonation this session is currently riding (data-model.md
    # §106, research.md R2-14). `NULL` for every ordinary session — this one
    # nullable pointer is the whole live-state mechanism: no second session
    # row and no second credential are ever created.
    #
    # Invariant maintained by the SERVICE, not the schema: a non-NULL value
    # here always points at an `impersonation_sessions` row whose `ended_at
    # IS NULL`. `get_principal` treats a pointer to a closed row as "not
    # impersonating" and clears it, so a crash between the two writes
    # degrades to the safe reading rather than to a stuck impersonation.
    impersonation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("impersonation_sessions.id"), nullable=True
    )


class CredentialSetupInvitation(Base):
    """A single-use, time-limited permission to set a password
    (data-model.md §6, R-01, FR-025 – FR-028)."""

    __tablename__ = "credential_setup_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    issued_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(nullable=True)


class SignInAttempt(Base):
    """Durable failed-attempt record backing the rate limit
    (data-model.md §7, R-06, FR-013, SC-011).

    Deliberately no foreign key to users — an attempt against a
    non-existent email is exactly the one worth recording.
    """

    __tablename__ = "sign_in_attempts"
    __table_args__ = (
        Index("ix_sign_in_attempts_email_time", "email", "attempted_at"),
        Index("ix_sign_in_attempts_ip_time", "client_ip", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    client_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    successful: Mapped[bool] = mapped_column(nullable=False)
