"""backfill_trainer_share_links

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-26

Data migration: create one player_standing ShareLink for every existing
trainer account that does not already have an active one. Written with
SQLAlchemy Core constructs against op.get_bind() — not raw SQL — so the
two documented raw-SQL exceptions in plan.md §Complexity Tracking stay at
two. Idempotent: re-running selects nothing to insert.
"""

import secrets
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _new_uuid() -> str:
    import uuid

    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()

    users = sa.Table("users", metadata, autoload_with=bind)
    share_links = sa.Table("share_links", metadata, autoload_with=bind)

    trainers_without_links = sa.select(users.c.id).where(
        users.c.role == "trainer",
        ~users.c.id.in_(
            sa.select(share_links.c.trainer_user_id).where(
                share_links.c.kind == "player_standing",
                share_links.c.is_active.is_(True),
            )
        ),
    )

    trainer_ids = [row[0] for row in bind.execute(trainers_without_links).fetchall()]

    if not trainer_ids:
        return

    now = _utcnow()
    rows = [
        {
            "id": _new_uuid(),
            "code": secrets.token_urlsafe(16),
            "trainer_user_id": trainer_id,
            "created_by_user_id": trainer_id,
            "kind": "player_standing",
            "target_email": None,
            "expires_at": None,
            "max_uses": None,
            "use_count": 0,
            "is_active": True,
            "revoked_at": None,
            "created_at": now,
        }
        for trainer_id in trainer_ids
    ]
    bind.execute(sa.insert(share_links), rows)


def downgrade() -> None:
    # A data backfill has no meaningful inverse — the links it created are
    # indistinguishable from ones a trainer might have regenerated since.
    # Nothing to do; the schema-level downgrade lives in revision 0005.
    pass
