from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid, utcnow


class TrainerPlayerAssociation(Base):
    """The many-to-many at the centre of multi-trainer support
    (data-model.md §17, FR-084 – FR-092).

    The unique constraint on (trainer_user_id, player_user_id) is what
    makes FR-082 true rather than merely checked: a second join attempt
    hits this index, and the service catches the conflict rather than
    raising the link's use count a second time.
    """

    __tablename__ = "trainer_player_associations"
    __table_args__ = (
        UniqueConstraint("trainer_user_id", "player_user_id", name="uq_trainer_player"),
        Index("ix_tpa_player_status", "player_user_id", "status"),
        Index("ix_tpa_trainer_status", "trainer_user_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    trainer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    share_link_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("share_links.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    joined_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow, onupdate=utcnow)


class LinkLookupAttempt(Base):
    """Durable counter behind the join-link throttle (data-model.md §18,
    FR-071, SC-021, research.md R-30), shaped like SignInAttempt.

    Deliberately no foreign key to anything — an invalid code identifies
    no account, and client_ip is the only dimension worth counting.
    """

    __tablename__ = "link_lookup_attempts"
    __table_args__ = (Index("ix_link_lookup_attempts_ip_time", "client_ip", "attempted_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    successful: Mapped[bool] = mapped_column(nullable=False)
