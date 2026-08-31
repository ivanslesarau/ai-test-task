from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_uuid, utcnow
from app.models.enums import Gender, PlayerProfileKind

_KIND_VALUES = ", ".join(f"'{k.value}'" for k in PlayerProfileKind)
_GENDER_VALUES = ", ".join(f"'{g.value}'" for g in Gender)


class PlayerProfile(Base):
    """One player who trains (data-model.md §26, FR-106, FR-107).

    Replaces `player_details`, whose primary key *was* `user_id` — a schema
    that asserted one player per account. FR-106 removes that assertion, so
    this table carries a surrogate key and an `account_user_id` foreign key
    instead, and it is this row — not the account — that a trainer
    association, a training context, and an approval request all reference
    (research.md R-34, R-35).

    `ck_player_profiles_self_names` is the constraint that makes R-37's two
    name sources unambiguous: a SELF profile's name and photo live on
    `user_profiles` and its own columns are NULL, while a CHILD profile
    carries its own, because a child without a sign-in has no `users` row
    to read from. The two cases are exhaustive and mutually exclusive, so
    no row can be ambiguous about which source is authoritative.

    Note the one duplication this design accepts (data-model.md §26.1): a
    child *with* a sign-in also needs the `user_profiles` row every account
    is required to have, so their name exists twice. This profile is
    authoritative, `family_service.update_profile` is the single writer of
    both, and nothing reads the copy.
    """

    __tablename__ = "player_profiles"
    __table_args__ = (
        CheckConstraint(f"kind IN ({_KIND_VALUES})", name="ck_player_profiles_kind"),
        CheckConstraint(
            f"gender IS NULL OR gender IN ({_GENDER_VALUES})",
            name="ck_player_profiles_gender",
        ),
        CheckConstraint(
            "(kind = 'self' AND first_name IS NULL AND last_name IS NULL)"
            " OR (kind = 'child' AND first_name IS NOT NULL AND last_name IS NOT NULL)",
            name="ck_player_profiles_self_names",
        ),
        CheckConstraint(
            "sign_in_user_id IS NULL OR kind = 'child'",
            name="ck_player_profiles_signin_is_child",
        ),
        # Partial unique index: at most one SELF profile per account
        # (FR-106). Partial rather than plain, because CHILD profiles are
        # unlimited. This is what makes "one account holder" true by
        # construction rather than checked in a service, so two concurrent
        # submissions produce one profile instead of racing.
        Index(
            "uq_player_profiles_one_self",
            "account_user_id",
            unique=True,
            sqlite_where=text(f"kind = '{PlayerProfileKind.SELF.value}'"),
        ),
        Index("ix_player_profiles_account_removed", "account_user_id", "removed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    account_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)

    # NULL exactly when kind == 'self' — the name is then the account's
    # (research.md R-37), enforced by ck_player_profiles_self_names.
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    photo_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Nullable only so revision 0009 can migrate rows that never had one.
    # Required by the schema on every new write (data-model.md §26).
    date_of_birth: Mapped[date | None] = mapped_column(nullable=True)
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    school: Mapped[str | None] = mapped_column(String(200), nullable=True)
    jersey_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Never writable by the family (FR-107, FR-007).
    skill_level: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # The one per-child permission (FR-146, research.md R-44). The default
    # lives in the schema because it is a safety property: a row created by
    # any path, including a future import, must not accidentally grant
    # unsupervised spending.
    tokens_without_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    # The child's own account when the parent granted one (FR-129). Unique
    # so one credential belongs to one child.
    sign_in_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, unique=True
    )

    # Soft removal (FR-111). NULL means the profile is live. A timestamp
    # rather than a status enum: it says when as well as whether, and it
    # avoids a third enum needing its own transition table.
    removed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow, onupdate=utcnow)

    # This profile's "last revised" stamp for its weekly availability
    # (data-model.md §104, research.md R2-09). `NULL` = never stated;
    # written on every accepted save and on a clear, which is why it
    # cannot be derived from `availability_slots` — a cleared week has no
    # rows there.
    availability_updated_at: Mapped[datetime | None] = mapped_column(nullable=True)


class ActiveTrainingContext(Base):
    """Which player profile and trainer a signed-in account is looking at
    (data-model.md §27, FR-117, FR-120, research.md R-36).

    Replaces `player_details.active_trainer_user_id`. Two facts moved it off
    the player's row: a parent's context *names* a profile, so it cannot
    live on one without a child's row pointing at a sibling; and a parent
    and a signed-in child both need a context over the same set of
    profiles. So the context belongs to the **viewer**, which is why this
    table is keyed by `user_id`.

    The stored pair is never trusted as read. `TrainingContextService`
    validates it and repairs a pair whose profile was removed, whose
    association is no longer active, or whose trainer is no longer active —
    FR-120 implemented once rather than at each caller.
    """

    __tablename__ = "active_training_contexts"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Both nullable together — holding no live association is a valid
    # state. A row with one set and the other NULL is never written, and
    # the resolver treats it as no context at all.
    player_profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("player_profiles.id"), nullable=True
    )
    trainer_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow, onupdate=utcnow)
