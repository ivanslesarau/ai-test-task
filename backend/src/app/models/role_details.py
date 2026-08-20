from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TrainerOrganization(Base):
    """Business identity for a trainer account (data-model.md §4.1).

    Later epics extend this table with billing identifiers, subscription
    status, and platform fee — not created here; those belong to Epic-05.
    """

    __tablename__ = "trainer_organizations"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)


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


class PlayerDetail(Base):
    """A player's participation attributes (data-model.md §4.3).

    `skill_level` is never writable through the profile API (FR-007,
    FR-033) and is free text rather than an enum because Epic-01 open
    question Q-01.01 leaves the vocabulary undecided.
    """

    __tablename__ = "player_details"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    school: Mapped[str | None] = mapped_column(String(200), nullable=True)
    jersey_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    skill_level: Mapped[str | None] = mapped_column(String(50), nullable=True)


class ParentContact(Base):
    """Emergency contact information for a player_parent account
    (data-model.md §4.4). Child profiles and parent-child links are out of
    scope for this feature.
    """

    __tablename__ = "parent_contacts"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emergency_contact_relation: Mapped[str | None] = mapped_column(String(100), nullable=True)
