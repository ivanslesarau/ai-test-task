from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid, utcnow


class ShareLink(Base):
    """A trainer's standing invitation link (data-model.md §16, FR-065 –
    FR-069).

    `code` is stored **in clear**, unlike every other secret in this
    system (sessions, setup invitations, which store only a SHA-256).
    FR-069 requires the trainer to read the code back at any time, which a
    hash makes impossible, and the link is designed to be published on a
    flyer — its confidentiality is not a security property (research.md
    R-21). What it grants is one thing the trainer is already offering
    publicly: the right to become their player.
    """

    __tablename__ = "share_links"
    __table_args__ = (Index("ix_share_links_trainer_active", "trainer_user_id", "is_active"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    trainer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    target_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
