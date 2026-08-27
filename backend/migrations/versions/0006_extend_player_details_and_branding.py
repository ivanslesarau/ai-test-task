"""extend_player_details_and_branding

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-26

Extension: five columns on player_details (US-01.02: player_name,
date_of_birth, gender, is_self, active_trainer_user_id) and three on
trainer_organizations (US-01.14: logo_key, primary_color,
branding_updated_at). All nullable or server-defaulted, so no table
rewrite is needed for existing rows (data-model.md §19).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("player_details") as batch_op:
        batch_op.add_column(sa.Column("player_name", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("date_of_birth", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("gender", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("is_self", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(
            sa.Column("active_trainer_user_id", sa.String(length=36), nullable=True)
        )
        batch_op.create_check_constraint(
            "ck_player_details_gender",
            "gender IN ('male','female','other','prefer_not_to_say')",
        )
        batch_op.create_foreign_key(
            "fk_player_details_active_trainer", "users", ["active_trainer_user_id"], ["id"]
        )

    op.create_index(
        op.f("ix_player_details_active_trainer_user_id"),
        "player_details",
        ["active_trainer_user_id"],
        unique=False,
    )

    with op.batch_alter_table("trainer_organizations") as batch_op:
        batch_op.add_column(sa.Column("logo_key", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("primary_color", sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column("branding_updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("trainer_organizations") as batch_op:
        batch_op.drop_column("branding_updated_at")
        batch_op.drop_column("primary_color")
        batch_op.drop_column("logo_key")

    op.drop_index(op.f("ix_player_details_active_trainer_user_id"), table_name="player_details")

    with op.batch_alter_table("player_details") as batch_op:
        batch_op.drop_constraint("fk_player_details_active_trainer", type_="foreignkey")
        batch_op.drop_constraint("ck_player_details_gender", type_="check")
        batch_op.drop_column("active_trainer_user_id")
        batch_op.drop_column("is_self")
        batch_op.drop_column("gender")
        batch_op.drop_column("date_of_birth")
        batch_op.drop_column("player_name")
