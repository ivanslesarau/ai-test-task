"""coach_invitations_availability_impersonation

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-28

Feature 002 (specs/002-coach-availability-impersonation), Phase 2 schema
(data-model.md §101 - §110). Single additive revision: three new tables
(`coach_invitations`, `availability_slots`, `impersonation_sessions`,
the last with its own pair of append-only triggers), and six new nullable
columns across four existing tables. No existing column changes type,
nullability, or meaning, and no data is migrated — every added column is
correct as NULL for every existing row.

*** WARNING (research.md R2-17) ***
`audit_entries.impersonator_user_id` below is added with a PLAIN
`op.add_column("audit_entries", ...)` call — it MUST NEVER be added
through `op.batch_alter_table`. Alembic's SQLite batch mode implements an
ALTER by creating a new table, copying rows, dropping the original, and
renaming — and dropping the table drops the two append-only triggers
revision 0004 installed on it (`trg_audit_entries_no_update`,
`trg_audit_entries_no_delete`). That would leave a green test suite and
a silently unprotected audit table. SQLite supports
`ALTER TABLE ... ADD COLUMN` natively for a nullable column with no
default, so batch mode is not needed here at all. The same caution is
why the two new `impersonation_sessions` triggers below are created with
`op.execute` immediately after that table, rather than added later
through a batch operation.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. coach_invitations (data-model.md §101) ----------------------------
    op.create_table(
        "coach_invitations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trainer_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_email", sa.String(length=320), nullable=False),
        sa.Column("invitee_name", sa.String(length=200), nullable=True),
        sa.Column("message", sa.String(length=2000), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.Column("superseded_by_id", sa.String(length=36), nullable=True),
        sa.Column("blocked_at", sa.DateTime(), nullable=True),
        sa.Column("blocked_reason", sa.String(), nullable=True),
        sa.CheckConstraint(
            "state IN ('awaiting','accepted','revoked','superseded')",
            name="ck_coach_invitations_state",
        ),
        sa.CheckConstraint(
            "blocked_reason IS NULL OR blocked_reason IN ('role_not_coach','already_assigned')",
            name="ck_coach_invitations_block_reason",
        ),
        sa.CheckConstraint(
            "(blocked_at IS NULL) = (blocked_reason IS NULL)",
            name="ck_coach_invitations_blocked_pair",
        ),
        sa.CheckConstraint(
            "(accepted_at IS NULL) = (accepted_by_user_id IS NULL)",
            name="ck_coach_invitations_accepted_pair",
        ),
        sa.CheckConstraint(
            "state <> 'accepted' OR accepted_at IS NOT NULL",
            name="ck_coach_invitations_terminal_pair",
        ),
        sa.ForeignKeyConstraint(["trainer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["coach_invitations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coach_invitations_trainer_state",
        "coach_invitations",
        ["trainer_user_id", "state"],
        unique=False,
    )
    op.create_index(
        "uq_coach_invitations_token_hash", "coach_invitations", ["token_hash"], unique=True
    )
    op.create_index(
        "ix_coach_invitations_trainer_email",
        "coach_invitations",
        ["trainer_user_id", "invited_email"],
        unique=False,
    )

    # 2. availability_slots (data-model.md §103) ----------------------------
    op.create_table(
        "availability_slots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("coach_user_id", sa.String(length=36), nullable=True),
        sa.Column("player_profile_id", sa.String(length=36), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=False),
        sa.Column("end_minute", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(coach_user_id IS NULL) <> (player_profile_id IS NULL)",
            name="ck_availability_slots_one_owner",
        ),
        sa.CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_availability_slots_day"),
        sa.CheckConstraint("start_minute < end_minute", name="ck_availability_slots_order"),
        sa.CheckConstraint(
            "start_minute >= 0 AND end_minute <= 1440", name="ck_availability_slots_bounds"
        ),
        sa.CheckConstraint(
            "start_minute % 15 = 0 AND end_minute % 15 = 0", name="ck_availability_slots_grid"
        ),
        sa.ForeignKeyConstraint(["coach_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_profile_id"], ["player_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_availability_slots_coach_day",
        "availability_slots",
        ["coach_user_id", "day_of_week"],
        unique=False,
    )
    op.create_index(
        "ix_availability_slots_profile_day",
        "availability_slots",
        ["player_profile_id", "day_of_week"],
        unique=False,
    )

    # 3. impersonation_sessions (data-model.md §105), then its triggers -----
    op.create_table(
        "impersonation_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("admin_user_id", sa.String(length=36), nullable=False),
        sa.Column("target_user_id", sa.String(length=36), nullable=False),
        sa.Column("auth_session_id", sa.String(length=36), nullable=True),
        sa.Column("target_status_at_start", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("end_reason", sa.String(), nullable=True),
        sa.CheckConstraint(
            "(ended_at IS NULL) = (end_reason IS NULL)",
            name="ck_impersonation_sessions_end_pair",
        ),
        sa.CheckConstraint(
            "end_reason IS NULL OR end_reason IN ("
            "'exited','timed_out','signed_out','superseded',"
            "'target_deactivated','target_erased','admin_deactivated')",
            name="ck_impersonation_sessions_end_reason",
        ),
        sa.CheckConstraint(
            "target_status_at_start IN ('active','inactive')",
            name="ck_impersonation_sessions_status_at_start",
        ),
        sa.CheckConstraint(
            "admin_user_id <> target_user_id", name="ck_impersonation_sessions_not_self"
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_impersonation_sessions_order",
        ),
        # No FK on auth_session_id — deliberate (data-model.md §105, research.md R2-18).
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_impersonation_sessions_admin",
        "impersonation_sessions",
        ["admin_user_id", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_impersonation_sessions_target",
        "impersonation_sessions",
        ["target_user_id", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_impersonation_sessions_open",
        "impersonation_sessions",
        ["admin_user_id"],
        unique=False,
        sqlite_where=sa.text("ended_at IS NULL"),
    )

    op.execute(
        """
        CREATE TRIGGER trg_impersonation_sessions_no_delete
        BEFORE DELETE ON impersonation_sessions
        BEGIN
            SELECT RAISE(ABORT, 'impersonation_sessions is append-only: DELETE is forbidden');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_impersonation_sessions_no_update_closed
        BEFORE UPDATE ON impersonation_sessions
        WHEN OLD.ended_at IS NOT NULL
           OR NEW.started_at <> OLD.started_at
           OR NEW.admin_user_id <> OLD.admin_user_id
           OR NEW.target_user_id <> OLD.target_user_id
        BEGIN
            SELECT RAISE(ABORT,
                'impersonation_sessions is append-only: only closing an open row is allowed');
        END;
        """
    )

    # 4. coach_details (data-model.md §102, §104) ---------------------------
    # No triggers on this table, so batch mode is available for the CHECK
    # constraint the columns need (research.md R2-17's caution is specific
    # to audit_entries and impersonation_sessions).
    with op.batch_alter_table("coach_details") as batch_op:
        batch_op.add_column(sa.Column("trainer_user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("joined_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("availability_updated_at", sa.DateTime(), nullable=True))
        batch_op.create_check_constraint(
            "ck_coach_details_assignment_pair",
            "(trainer_user_id IS NULL) = (joined_at IS NULL)",
        )
        batch_op.create_foreign_key(
            "fk_coach_details_trainer_user_id", "users", ["trainer_user_id"], ["id"]
        )
        batch_op.create_index("ix_coach_details_trainer", ["trainer_user_id"])

    # 5. player_profiles (data-model.md §104) --------------------------------
    op.add_column(
        "player_profiles", sa.Column("availability_updated_at", sa.DateTime(), nullable=True)
    )

    # 6. sessions (data-model.md §106) ---------------------------------------
    # No triggers on this table either, so a batch operation is safe here —
    # used only to attach the foreign key alongside the column.
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(sa.Column("impersonation_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_sessions_impersonation_id",
            "impersonation_sessions",
            ["impersonation_id"],
            ["id"],
        )

    # 7. audit_entries (data-model.md §107) — PLAIN add_column only. See the
    # module-level warning: op.batch_alter_table here would silently drop
    # revision 0004's append-only triggers.
    #
    # This column also needs a foreign key to users.id (data-model.md
    # §107). Alembic's `op.add_column` refuses to attach a ForeignKey on
    # SQLite outside batch mode (it tries a separate ALTER ... ADD
    # CONSTRAINT, which SQLite has never supported at all, batch or not —
    # confirmed against alembic.ddl.sqlite.SQLiteImpl.add_constraint).
    # SQLite itself, however, natively accepts a REFERENCES clause inline
    # on `ALTER TABLE ... ADD COLUMN` as a single statement with no table
    # recreation — verified directly against sqlite3. `op.execute` is used
    # here for exactly that one statement, the same accepted raw-SQL
    # exception this revision already takes for CREATE TRIGGER (and that
    # revision 0004 took before it): there is no Core construct for it.
    op.execute(
        "ALTER TABLE audit_entries ADD COLUMN impersonator_user_id VARCHAR(36) REFERENCES users(id)"
    )
    op.create_index(
        "ix_audit_entries_impersonator",
        "audit_entries",
        ["impersonator_user_id"],
        unique=False,
        sqlite_where=sa.text("impersonator_user_id IS NOT NULL"),
    )


def downgrade() -> None:
    # 7. audit_entries — plain drop_column, natively supported since SQLite
    # 3.35. Same caution as the upgrade: no batch_alter_table on this table.
    op.drop_index("ix_audit_entries_impersonator", table_name="audit_entries")
    op.drop_column("audit_entries", "impersonator_user_id")

    # 6. sessions
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_constraint("fk_sessions_impersonation_id", type_="foreignkey")
        batch_op.drop_column("impersonation_id")

    # 5. player_profiles
    op.drop_column("player_profiles", "availability_updated_at")

    # 4. coach_details
    with op.batch_alter_table("coach_details") as batch_op:
        batch_op.drop_index("ix_coach_details_trainer")
        batch_op.drop_constraint("fk_coach_details_trainer_user_id", type_="foreignkey")
        batch_op.drop_constraint("ck_coach_details_assignment_pair", type_="check")
        batch_op.drop_column("availability_updated_at")
        batch_op.drop_column("joined_at")
        batch_op.drop_column("trainer_user_id")

    # 3. impersonation_sessions — drop the two triggers before the table.
    op.execute("DROP TRIGGER IF EXISTS trg_impersonation_sessions_no_update_closed")
    op.execute("DROP TRIGGER IF EXISTS trg_impersonation_sessions_no_delete")
    op.drop_index("ix_impersonation_sessions_open", table_name="impersonation_sessions")
    op.drop_index("ix_impersonation_sessions_target", table_name="impersonation_sessions")
    op.drop_index("ix_impersonation_sessions_admin", table_name="impersonation_sessions")
    op.drop_table("impersonation_sessions")

    # 2. availability_slots
    op.drop_index("ix_availability_slots_profile_day", table_name="availability_slots")
    op.drop_index("ix_availability_slots_coach_day", table_name="availability_slots")
    op.drop_table("availability_slots")

    # 1. coach_invitations
    op.drop_index("ix_coach_invitations_trainer_email", table_name="coach_invitations")
    op.drop_index("uq_coach_invitations_token_hash", table_name="coach_invitations")
    op.drop_index("ix_coach_invitations_trainer_state", table_name="coach_invitations")
    op.drop_table("coach_invitations")
