"""Revision 0007 backfills one player_standing ShareLink per existing
trainer (data-model.md §23). This test drives Alembic directly — not
through the db_session fixture, which already migrates to head before a
test body runs — so it can observe the backfill re-running on data it
already touched and prove idempotence (plan.md §Extension, tasks.md
T224).
"""

import asyncio
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

_ALEMBIC_INI_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


@pytest.fixture
async def migration_db(tmp_path: Path) -> str:
    # env.py's run_migrations_online() ignores the URL set on the passed
    # Config and instead reads app.core.config.get_settings().database_url
    # (see migrations/env.py) — so, exactly as conftest.py's db_session
    # fixture does, the environment variable is what actually routes
    # Alembic to this file.
    db_path = tmp_path / f"migration-backfill-{uuid.uuid4().hex}.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    os.environ["DATABASE_URL"] = database_url

    from app.core.config import get_settings

    get_settings.cache_clear()

    return database_url


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(_ALEMBIC_INI_PATH))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


async def test_backfill_creates_one_active_link_per_trainer_and_is_idempotent(
    migration_db: str,
) -> None:
    cfg = _alembic_config(migration_db)

    # Migrate only as far as 0006, then seed two trainers with no link —
    # exactly the "existing trainer, pre-extension" state 0007 targets.
    await asyncio.to_thread(command.upgrade, cfg, "0006")

    engine = create_async_engine(migration_db)
    async with engine.begin() as conn:
        for i in range(2):
            user_id = f"trainer-{i}-{uuid.uuid4().hex}"
            await conn.execute(
                text(
                    "INSERT INTO users (id, email, role, status, version, created_at, updated_at) "
                    "VALUES (:id, :email, 'trainer', 'active', 1, '2026-01-01', '2026-01-01')"
                ),
                {"id": user_id, "email": f"trainer-{i}-{uuid.uuid4().hex}@example.org"},
            )
    await engine.dispose()

    # First run: 0007's upgrade() should create exactly one link per trainer.
    await asyncio.to_thread(command.upgrade, cfg, "0007")

    engine = create_async_engine(migration_db)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT trainer_user_id, code FROM share_links "
                "WHERE kind = 'player_standing' AND is_active = 1"
            )
        )
        rows = result.fetchall()
    await engine.dispose()

    assert len(rows) == 2
    codes = [row[1] for row in rows]
    assert len(set(codes)) == 2, "backfilled codes must be unique"
    assert all(len(code) >= 22 for code in codes), "backfilled codes must carry full entropy"

    # Second run: downgrade only unwinds the alembic_version pointer (0007's
    # downgrade() is a documented no-op — a data backfill has no inverse),
    # so the rows from the first run are still present. Re-running upgrade
    # must not create duplicates.
    await asyncio.to_thread(command.downgrade, cfg, "0006")
    await asyncio.to_thread(command.upgrade, cfg, "0007")

    engine = create_async_engine(migration_db)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT trainer_user_id, COUNT(*) FROM share_links "
                "WHERE kind = 'player_standing' AND is_active = 1 "
                "GROUP BY trainer_user_id"
            )
        )
        counts = result.fetchall()
    await engine.dispose()

    assert len(counts) == 2
    assert all(count == 1 for _, count in counts), (
        "re-running the backfill must not duplicate links"
    )
