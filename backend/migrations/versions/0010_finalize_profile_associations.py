"""finalize_profile_associations

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-27

Extension (family accounts), constraint step 3 of 3 (data-model.md §33,
research.md R-35). Under batch_alter_table: makes player_profile_id
non-nullable, swaps uq_trainer_player onto (trainer_user_id,
player_profile_id), swaps ix_tpa_player_status onto (player_profile_id,
status), and drops player_user_id. Then drops the player_details table.

Every player_parent account is created with exactly one PlayerDetail row
(both insert_account and insert_join_registration in user_repository.py
create one unconditionally), so revision 0009 leaves no association
without a player_profile_id — this revision's NOT NULL is safe.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("trainer_player_associations") as batch_op:
        batch_op.drop_constraint("uq_trainer_player", type_="unique")
        batch_op.drop_index("ix_tpa_player_status")
        batch_op.alter_column(
            "player_profile_id", existing_type=sa.String(length=36), nullable=False
        )
        batch_op.create_unique_constraint(
            "uq_trainer_player", ["trainer_user_id", "player_profile_id"]
        )
        batch_op.create_index("ix_tpa_player_status", ["player_profile_id", "status"], unique=False)
        batch_op.drop_index("ix_trainer_player_associations_player_user_id")
        batch_op.drop_column("player_user_id")

    op.drop_table("player_details")


def downgrade() -> None:
    op.create_table(
        "player_details",
        sa.Column("user_id", sa.String(length=36), primary_key=True),
        sa.Column("school", sa.String(length=200), nullable=True),
        sa.Column("jersey_number", sa.String(length=10), nullable=True),
        sa.Column("skill_level", sa.String(length=50), nullable=True),
        sa.Column("player_name", sa.String(length=200), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(), nullable=True),
        sa.Column("is_self", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("active_trainer_user_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["active_trainer_user_id"], ["users.id"]),
        sa.CheckConstraint(
            "gender IS NULL OR gender IN ('male','female','other','prefer_not_to_say')",
            name="ck_player_details_gender",
        ),
    )
    op.create_index(
        op.f("ix_player_details_active_trainer_user_id"),
        "player_details",
        ["active_trainer_user_id"],
        unique=False,
    )

    with op.batch_alter_table("trainer_player_associations") as batch_op:
        batch_op.add_column(sa.Column("player_user_id", sa.String(length=36), nullable=True))
        batch_op.create_index(
            op.f("ix_trainer_player_associations_player_user_id"),
            ["player_user_id"],
        )
        batch_op.drop_index("ix_tpa_player_status")
        batch_op.drop_constraint("uq_trainer_player", type_="unique")
        batch_op.alter_column(
            "player_profile_id", existing_type=sa.String(length=36), nullable=True
        )
        batch_op.create_index("ix_tpa_player_status", ["player_user_id", "status"], unique=False)
        batch_op.create_unique_constraint(
            "uq_trainer_player", ["trainer_user_id", "player_user_id"]
        )

    # player_user_id and player_details rows are repopulated by revision
    # 0009's downgrade, which runs after this one during a full
    # `alembic downgrade`. This revision only restores the shape.
