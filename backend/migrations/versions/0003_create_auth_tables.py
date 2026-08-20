"""create_auth_tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_sessions_token_hash"), "sessions", ["token_hash"], unique=True)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)

    op.create_table(
        "credential_setup_invitations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("issued_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_credential_setup_invitations_token_hash"),
        "credential_setup_invitations",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_credential_setup_invitations_user_id"),
        "credential_setup_invitations",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "sign_in_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("client_ip", sa.String(length=45), nullable=False),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.Column("successful", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sign_in_attempts_email_time",
        "sign_in_attempts",
        ["email", "attempted_at"],
        unique=False,
    )
    op.create_index(
        "ix_sign_in_attempts_ip_time",
        "sign_in_attempts",
        ["client_ip", "attempted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sign_in_attempts_ip_time", table_name="sign_in_attempts")
    op.drop_index("ix_sign_in_attempts_email_time", table_name="sign_in_attempts")
    op.drop_table("sign_in_attempts")

    op.drop_index(
        op.f("ix_credential_setup_invitations_user_id"),
        table_name="credential_setup_invitations",
    )
    op.drop_index(
        op.f("ix_credential_setup_invitations_token_hash"),
        table_name="credential_setup_invitations",
    )
    op.drop_table("credential_setup_invitations")

    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_token_hash"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_expires_at"), table_name="sessions")
    op.drop_table("sessions")
