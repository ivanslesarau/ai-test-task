from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TrainerOrganization(Base):
    """Business identity for a trainer account (data-model.md §4.1, §19.2).

    Later epics extend this table with billing identifiers, subscription
    status, and platform fee — not created here; those belong to Epic-05.

    `logo_key` and `primary_color` were added by the 2026-08-26 extension
    (US-01.14). Both are nullable and mean "platform default" when absent
    — never an empty string (constitution Principle VI, FR-104).
    """

    __tablename__ = "trainer_organizations"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    logo_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    branding_updated_at: Mapped[datetime | None] = mapped_column(nullable=True)


class CoachDetail(Base):
    """A coach's professional presentation (data-model.md §4.2).

    The single-trainer assignment Epic-01 describes is out of scope; no
    column for it exists here.
    """

    __tablename__ = "coach_details"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    bio: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    credentials: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    certifications: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_publicly_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ParentContact(Base):
    """Emergency contact information for a player_parent account
    (data-model.md §4.4, §29.3). Held once against the account and
    serving every player profile on it — the family's single contact
    record, now load-bearing since FR-113 makes it what a trainer reaches
    to contact the responsible adult for a CHILD profile as well as a
    SELF one.

    `player_details` — which used to sit alongside this table — is
    dropped (data-model.md §29.2). Its columns now live on
    `player_profiles` (`app.models.player_profile`), which is
    per-profile rather than per-account (research.md R-34).
    """

    __tablename__ = "parent_contacts"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emergency_contact_relation: Mapped[str | None] = mapped_column(String(100), nullable=True)
