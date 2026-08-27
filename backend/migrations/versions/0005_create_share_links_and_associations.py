"""create_share_links_and_associations

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-26

Extension: ShareLink invitation links, trainer-player associations, and
the link-lookup throttle counter (data-model.md §16 - §18, FR-065 -
FR-071, FR-084 - FR-092).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "share_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("trainer_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("target_email", sa.String(length=320), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('player_standing','coach_single_use')", name="ck_share_links_kind"
        ),
        sa.ForeignKeyConstraint(["trainer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_share_links_code"), "share_links", ["code"], unique=True)
    op.create_index(
        op.f("ix_share_links_trainer_user_id"), "share_links", ["trainer_user_id"], unique=False
    )
    op.create_index(
        "ix_share_links_trainer_active",
        "share_links",
        ["trainer_user_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "trainer_player_associations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trainer_user_id", sa.String(length=36), nullable=False),
        sa.Column("player_user_id", sa.String(length=36), nullable=False),
        sa.Column("share_link_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_tpa_status"),
        sa.ForeignKeyConstraint(["trainer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["share_link_id"], ["share_links.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trainer_user_id", "player_user_id", name="uq_trainer_player"),
    )
    op.create_index(
        op.f("ix_trainer_player_associations_trainer_user_id"),
        "trainer_player_associations",
        ["trainer_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_trainer_player_associations_player_user_id"),
        "trainer_player_associations",
        ["player_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_tpa_player_status",
        "trainer_player_associations",
        ["player_user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_tpa_trainer_status",
        "trainer_player_associations",
        ["trainer_user_id", "status"],
        unique=False,
    )

    op.create_table(
        "link_lookup_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_ip", sa.String(length=45), nullable=False),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.Column("successful", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_link_lookup_attempts_ip_time",
        "link_lookup_attempts",
        ["client_ip", "attempted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_link_lookup_attempts_ip_time", table_name="link_lookup_attempts")
    op.drop_table("link_lookup_attempts")

    op.drop_index("ix_tpa_trainer_status", table_name="trainer_player_associations")
    op.drop_index("ix_tpa_player_status", table_name="trainer_player_associations")
    op.drop_index(
        op.f("ix_trainer_player_associations_player_user_id"),
        table_name="trainer_player_associations",
    )
    op.drop_index(
        op.f("ix_trainer_player_associations_trainer_user_id"),
        table_name="trainer_player_associations",
    )
    op.drop_table("trainer_player_associations")

    op.drop_index("ix_share_links_trainer_active", table_name="share_links")
    op.drop_index(op.f("ix_share_links_trainer_user_id"), table_name="share_links")
    op.drop_index(op.f("ix_share_links_code"), table_name="share_links")
    op.drop_table("share_links")
