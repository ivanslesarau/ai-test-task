"""create_player_profiles_and_approvals

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-27

Extension (family accounts), structure step 1 of 3 (data-model.md §33,
research.md R-35). Creates player_profiles, active_training_contexts, and
approval_requests, and adds trainer_player_associations.player_profile_id
as NULLABLE. Nothing is dropped and nothing is required, so the
application keeps running unchanged on this revision — the data backfill
is revision 0009 and the constraint finalization is revision 0010.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "player_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "account_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("photo_key", sa.String(length=128), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(), nullable=True),
        sa.Column("school", sa.String(length=200), nullable=True),
        sa.Column("jersey_number", sa.String(length=10), nullable=True),
        sa.Column("skill_level", sa.String(length=50), nullable=True),
        sa.Column(
            "tokens_without_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "sign_in_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id"),
            nullable=True,
            unique=True,
        ),
        sa.Column("removed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("kind IN ('self','child')", name="ck_player_profiles_kind"),
        sa.CheckConstraint(
            "gender IS NULL OR gender IN ('male','female','other','prefer_not_to_say')",
            name="ck_player_profiles_gender",
        ),
        sa.CheckConstraint(
            "(kind = 'self' AND first_name IS NULL AND last_name IS NULL)"
            " OR (kind = 'child' AND first_name IS NOT NULL AND last_name IS NOT NULL)",
            name="ck_player_profiles_self_names",
        ),
        sa.CheckConstraint(
            "sign_in_user_id IS NULL OR kind = 'child'",
            name="ck_player_profiles_signin_is_child",
        ),
    )
    op.create_index(
        op.f("ix_player_profiles_account_user_id"),
        "player_profiles",
        ["account_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_player_profiles_account_removed",
        "player_profiles",
        ["account_user_id", "removed_at"],
        unique=False,
    )
    op.create_index(
        "uq_player_profiles_one_self",
        "player_profiles",
        ["account_user_id"],
        unique=True,
        sqlite_where=sa.text("kind = 'self'"),
    )

    op.create_table(
        "active_training_contexts",
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "player_profile_id",
            sa.String(length=36),
            sa.ForeignKey("player_profiles.id"),
            nullable=True,
        ),
        sa.Column(
            "trainer_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "player_profile_id",
            sa.String(length=36),
            sa.ForeignKey("player_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending_parent_approval"),
        sa.Column(
            "trainer_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column(
            "share_link_id", sa.String(length=36), sa.ForeignKey("share_links.id"), nullable=True
        ),
        sa.Column("amount_minor", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("parent_note", sa.String(length=1000), nullable=True),
        sa.Column("child_note", sa.String(length=1000), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "resolved_by_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.CheckConstraint(
            "kind IN ('join_trainer','usd_payment','token_spend')",
            name="ck_approval_requests_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending_parent_approval','info_requested','approved',"
            "'denied','expired','withdrawn')",
            name="ck_approval_requests_status",
        ),
        sa.CheckConstraint(
            "(kind = 'join_trainer' AND trainer_user_id IS NOT NULL"
            " AND amount_minor IS NULL AND currency IS NULL)"
            " OR (kind IN ('usd_payment','token_spend') AND amount_minor IS NOT NULL"
            " AND currency IS NOT NULL AND trainer_user_id IS NULL)",
            name="ck_approval_requests_subject",
        ),
        sa.CheckConstraint(
            "(status IN ('pending_parent_approval','info_requested') AND resolved_at IS NULL)"
            " OR (status IN ('approved','denied','expired','withdrawn')"
            " AND resolved_at IS NOT NULL)",
            name="ck_approval_requests_resolution",
        ),
        sa.CheckConstraint(
            "status <> 'expired' OR resolved_by_user_id IS NULL",
            name="ck_approval_requests_expiry_actor",
        ),
    )
    op.create_index(
        op.f("ix_approval_requests_player_profile_id"),
        "approval_requests",
        ["player_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_approval_requests_parent_user_id"),
        "approval_requests",
        ["parent_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_approval_requests_expires_at"), "approval_requests", ["expires_at"], unique=False
    )
    op.create_index(
        "ix_approval_requests_parent_status",
        "approval_requests",
        ["parent_user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_approval_requests_profile_status",
        "approval_requests",
        ["player_profile_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_approval_requests_status_expiry",
        "approval_requests",
        ["status", "expires_at"],
        unique=False,
    )
    op.create_index(
        "uq_approval_requests_live",
        "approval_requests",
        ["player_profile_id", "kind", "trainer_user_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('pending_parent_approval','info_requested')"),
    )

    with op.batch_alter_table("trainer_player_associations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "player_profile_id",
                sa.String(length=36),
                sa.ForeignKey(
                    "player_profiles.id",
                    ondelete="CASCADE",
                    name="fk_tpa_player_profile_id",
                ),
                nullable=True,
            )
        )
    op.create_index(
        "ix_tpa_profile_status",
        "trainer_player_associations",
        ["player_profile_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_trainer_player_associations_player_profile_id"),
        "trainer_player_associations",
        ["player_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_trainer_player_associations_player_profile_id"),
        table_name="trainer_player_associations",
    )
    op.drop_index("ix_tpa_profile_status", table_name="trainer_player_associations")
    with op.batch_alter_table("trainer_player_associations") as batch_op:
        batch_op.drop_column("player_profile_id")

    op.drop_table("approval_requests")
    op.drop_table("active_training_contexts")
    op.drop_table("player_profiles")
