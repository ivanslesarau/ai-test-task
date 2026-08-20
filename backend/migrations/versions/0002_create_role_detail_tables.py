"""create_role_detail_tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trainer_organizations",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "coach_details",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("bio", sa.String(length=2000), nullable=True),
        sa.Column("credentials", sa.String(length=1000), nullable=True),
        sa.Column("certifications", sa.String(length=1000), nullable=True),
        sa.Column("is_publicly_visible", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "player_details",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("school", sa.String(length=200), nullable=True),
        sa.Column("jersey_number", sa.String(length=10), nullable=True),
        sa.Column("skill_level", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "parent_contacts",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("emergency_contact_name", sa.String(length=200), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(length=32), nullable=True),
        sa.Column("emergency_contact_relation", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("parent_contacts")
    op.drop_table("player_details")
    op.drop_table("coach_details")
    op.drop_table("trainer_organizations")
