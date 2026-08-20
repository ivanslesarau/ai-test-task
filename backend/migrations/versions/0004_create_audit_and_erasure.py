"""create_audit_and_erasure

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-19

Includes the append-only triggers on audit_entries — the second documented
raw-SQL exception in plan.md §Complexity Tracking. FR-055 requires that no
one can alter or remove an audit entry through the platform; the repository
having no update/delete method is the primary control, and these triggers
are defence in depth against a future migration or script that bypasses it.
CREATE TRIGGER is not expressible as an ORM or Core construct.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("target_user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("detail", sa.String(length=2000), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_entries_action", "audit_entries", ["action"], unique=False)
    op.create_index("ix_audit_entries_occurred_at", "audit_entries", ["occurred_at"], unique=False)
    op.create_index("ix_audit_entries_target", "audit_entries", ["target_user_id"], unique=False)

    op.create_table(
        "erasure_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("original_email", sa.String(length=320), nullable=False),
        sa.Column("original_first_name", sa.String(length=100), nullable=False),
        sa.Column("original_last_name", sa.String(length=100), nullable=False),
        sa.Column("erased_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("erased_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["erased_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.execute(
        """
        CREATE TRIGGER trg_audit_entries_no_update
        BEFORE UPDATE ON audit_entries
        BEGIN
            SELECT RAISE(ABORT, 'audit_entries is append-only: UPDATE is forbidden');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_entries_no_delete
        BEFORE DELETE ON audit_entries
        BEGIN
            SELECT RAISE(ABORT, 'audit_entries is append-only: DELETE is forbidden');
        END;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_entries_no_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_entries_no_update")
    op.drop_table("erasure_records")
    op.drop_index("ix_audit_entries_target", table_name="audit_entries")
    op.drop_index("ix_audit_entries_occurred_at", table_name="audit_entries")
    op.drop_index("ix_audit_entries_action", table_name="audit_entries")
    op.drop_table("audit_entries")
