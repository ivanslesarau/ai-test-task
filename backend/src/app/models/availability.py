from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid, utcnow


class AvailabilitySlot(Base):
    """One stated range of one day of one person's week (data-model.md
    §103, FR-024 – FR-032). One table serves both owner kinds — a coach
    (`coach_user_id`) or a player profile (`player_profile_id`) — with a
    CHECK constraint making exactly one owner true by construction
    (research.md R2-07); two real foreign keys beat a polymorphic
    `(subject_kind, subject_id)` pair because referential integrity holds
    in both directions and `ON DELETE CASCADE` does the right thing on a
    hard delete.

    Times are integer minutes from midnight on a 15-minute grid
    (research.md R2-08) — no `TIME` column, because SQLite has none and
    stores one as text. `end_minute` may reach 1440 (midnight); `start <
    end` then forbids a range crossing it.

    The six-ranges-per-day ceiling (FR-028) and the no-overlap rule
    (FR-027) are properties of a *set* of rows, so they are NOT enforced
    here — a SQLite CHECK cannot see other rows. They live in
    `AvailabilityService`'s whole-week validator (data-model.md §111.2).
    The single-row invariants below are duplicated in the database
    precisely because they *can* be, so no import, seed, or CLI path can
    introduce an off-grid or inverted slot.

    The week's own "last revised" timestamp does NOT live here — see
    `availability_updated_at` on `CoachDetail` and `PlayerProfile`
    (data-model.md §104, research.md R2-09): a cleared week has no slot
    rows, so a `MAX(created_at)` here could never answer "when was this
    person's week last touched".
    """

    __tablename__ = "availability_slots"
    __table_args__ = (
        CheckConstraint(
            "(coach_user_id IS NULL) <> (player_profile_id IS NULL)",
            name="ck_availability_slots_one_owner",
        ),
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_availability_slots_day"),
        CheckConstraint("start_minute < end_minute", name="ck_availability_slots_order"),
        CheckConstraint(
            "start_minute >= 0 AND end_minute <= 1440", name="ck_availability_slots_bounds"
        ),
        CheckConstraint(
            "start_minute % 15 = 0 AND end_minute % 15 = 0", name="ck_availability_slots_grid"
        ),
        Index("ix_availability_slots_coach_day", "coach_user_id", "day_of_week"),
        Index("ix_availability_slots_profile_day", "player_profile_id", "day_of_week"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    coach_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    player_profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("player_profiles.id", ondelete="CASCADE"), nullable=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
