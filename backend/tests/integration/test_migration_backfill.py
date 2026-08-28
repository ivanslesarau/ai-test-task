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


async def _seed_family_at_0007(database_url: str) -> dict[str, str]:
    """Seed one trainer, one self-player, and one child-player associated
    with the trainer, with the child's active context set — the shape
    revisions 0008-0010 must carry forward without loss (data-model.md
    §33, plan.md §Extension (2026-08-27) T320)."""
    engine = create_async_engine(database_url)
    ids = {
        "trainer": f"trainer-{uuid.uuid4().hex}",
        "self_player": f"self-{uuid.uuid4().hex}",
        "child_player": f"child-{uuid.uuid4().hex}",
        "association_self": uuid.uuid4().hex,
        "association_child": uuid.uuid4().hex,
    }
    async with engine.begin() as conn:
        for role_id, role in (
            (ids["trainer"], "trainer"),
            (ids["self_player"], "player_parent"),
            (ids["child_player"], "player_parent"),
        ):
            await conn.execute(
                text(
                    "INSERT INTO users (id, email, role, status, version, created_at, updated_at)"
                    " VALUES (:id, :email, :role, 'active', 1, '2026-01-01', '2026-01-01')"
                ),
                {"id": role_id, "email": f"{role_id}@example.org", "role": role},
            )
        # A self player with an active trainer context (exercises the
        # active_training_contexts backfill).
        await conn.execute(
            text(
                "INSERT INTO player_details (user_id, is_self, active_trainer_user_id)"
                " VALUES (:uid, 1, :trainer)"
            ),
            {"uid": ids["self_player"], "trainer": ids["trainer"]},
        )
        # A child player with a one-word name, to exercise the split
        # heuristic's edge case (research.md R-35).
        await conn.execute(
            text(
                "INSERT INTO player_details (user_id, is_self, player_name, date_of_birth,"
                " gender) VALUES (:uid, 0, 'Cher', '2015-01-01', 'female')"
            ),
            {"uid": ids["child_player"]},
        )
        for assoc_id, player_id in (
            (ids["association_self"], ids["self_player"]),
            (ids["association_child"], ids["child_player"]),
        ):
            await conn.execute(
                text(
                    "INSERT INTO trainer_player_associations"
                    " (id, trainer_user_id, player_user_id, status, joined_at, updated_at)"
                    " VALUES (:id, :trainer, :player, 'active', '2026-01-01', '2026-01-01')"
                ),
                {"id": assoc_id, "trainer": ids["trainer"], "player": player_id},
            )
    await engine.dispose()
    return ids


async def test_revision_0009_migrates_players_to_profiles_without_loss(
    migration_db: str,
) -> None:
    """The gate T320 names before Family Phase B may begin: revisions
    0008-0010 must not drop an association, must give every account with
    a former context exactly one active_training_contexts row, and running
    upgrade twice must be a no-op (data-model.md §33)."""
    cfg = _alembic_config(migration_db)
    await asyncio.to_thread(command.upgrade, cfg, "0007")
    ids = await _seed_family_at_0007(migration_db)

    await asyncio.to_thread(command.upgrade, cfg, "0010")

    engine = create_async_engine(migration_db)
    async with engine.connect() as conn:
        assoc_count = (
            await conn.execute(text("SELECT COUNT(*) FROM trainer_player_associations"))
        ).scalar_one()
        null_profile_associations = (
            await conn.execute(
                text(
                    "SELECT COUNT(*) FROM trainer_player_associations"
                    " WHERE player_profile_id IS NULL"
                )
            )
        ).scalar_one()
        profiles = (
            await conn.execute(
                text("SELECT id, account_user_id, kind, first_name, last_name FROM player_profiles")
            )
        ).fetchall()
        context_rows = (
            await conn.execute(
                text(
                    "SELECT user_id, player_profile_id, trainer_user_id FROM"
                    " active_training_contexts"
                )
            )
        ).fetchall()

        # player_details must be gone entirely.
        table_exists = (
            await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='player_details'")
            )
        ).fetchone()
    await engine.dispose()

    assert assoc_count == 2, "no association may be lost across 0007 -> 0010"
    assert null_profile_associations == 0, (
        "every association must end with a non-null player_profile_id"
    )
    assert table_exists is None, "player_details must be dropped by revision 0010"

    profiles_by_account = {row[1]: row for row in profiles}
    assert len(profiles) == 2
    self_profile = profiles_by_account[ids["self_player"]]
    assert self_profile[2] == "self"
    assert self_profile[3] is None and self_profile[4] is None, (
        "a self profile's name is NULL — it is read from user_profiles (research.md R-37)"
    )
    child_profile = profiles_by_account[ids["child_player"]]
    assert child_profile[2] == "child"
    assert child_profile[3] == "Cher", "the one-word name becomes the first name"
    assert child_profile[4] == "—", (
        "a one-word name's last name becomes the placeholder, never NULL"
        " (ck_player_profiles_self_names requires both on a child)"
    )

    assert len(context_rows) == 1, "exactly one account had a former context"
    context_user_id, context_profile_id, context_trainer_id = context_rows[0]
    assert context_user_id == ids["self_player"]
    assert context_profile_id == self_profile[0]
    assert context_trainer_id == ids["trainer"]

    # Idempotence: upgrading again from head must not duplicate anything.
    await asyncio.to_thread(command.upgrade, cfg, "0010")
    engine = create_async_engine(migration_db)
    async with engine.connect() as conn:
        profile_count_again = (
            await conn.execute(text("SELECT COUNT(*) FROM player_profiles"))
        ).scalar_one()
        assoc_count_again = (
            await conn.execute(text("SELECT COUNT(*) FROM trainer_player_associations"))
        ).scalar_one()
    await engine.dispose()
    assert profile_count_again == 2, "re-running upgrade must not create duplicate profiles"
    assert assoc_count_again == 2, "re-running upgrade must not touch associations again"


async def test_revision_0009_downgrade_raises_for_multi_profile_account(
    migration_db: str,
) -> None:
    """A clean reversal is impossible in principle once an account holds
    more than one profile — player_details is keyed one row per account.
    The downgrade must refuse loudly rather than silently discarding a
    family's second child (research.md R-35, data-model.md §33)."""
    cfg = _alembic_config(migration_db)
    await asyncio.to_thread(command.upgrade, cfg, "0010")

    engine = create_async_engine(migration_db)
    async with engine.begin() as conn:
        account_id = f"parent-{uuid.uuid4().hex}"
        await conn.execute(
            text(
                "INSERT INTO users (id, email, role, status, version, created_at, updated_at)"
                " VALUES (:id, :email, 'player_parent', 'active', 1, '2026-01-01', '2026-01-01')"
            ),
            {"id": account_id, "email": f"{account_id}@example.org"},
        )
        for i in range(2):
            await conn.execute(
                text(
                    "INSERT INTO player_profiles (id, account_user_id, kind, first_name,"
                    " last_name, tokens_without_approval, created_at, updated_at)"
                    " VALUES (:id, :account, 'child', :first, 'Test', 0,"
                    " '2026-01-01', '2026-01-01')"
                ),
                {"id": uuid.uuid4().hex, "account": account_id, "first": f"Child{i}"},
            )
    await engine.dispose()

    from alembic.util.exc import CommandError

    with pytest.raises((RuntimeError, CommandError)) as exc_info:
        await asyncio.to_thread(command.downgrade, cfg, "0007")
    assert "more than" in str(exc_info.value) or "player profile" in str(exc_info.value)

    # The database must still be usable and at a consistent revision —
    # not left half-migrated. Re-running upgrade head must succeed.
    await asyncio.to_thread(command.upgrade, cfg, "0010")
    engine = create_async_engine(migration_db)
    async with engine.connect() as conn:
        profile_count = (
            await conn.execute(text("SELECT COUNT(*) FROM player_profiles"))
        ).scalar_one()
    await engine.dispose()
    assert profile_count == 2, "the offending profiles must survive the failed downgrade attempt"
