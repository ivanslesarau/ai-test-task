"""Revision 0011 lands correctly (data-model.md §110, tasks.md T516,
quickstart.md §1).

Three checks that matter more than "the migration runs": the three new
tables exist, the six new columns exist, and — the trap research.md
R2-17 documents — revision 0004's two `audit_entries` append-only
triggers are still there after 0011 adds a column to that same table.
A round trip (`downgrade` then `upgrade`) must also leave the schema in
the same shape.
"""

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_ALEMBIC_INI_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


async def _table_names(db_session: AsyncSession) -> set[str]:
    rows = await db_session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    return {r[0] for r in rows}


async def _trigger_names(db_session: AsyncSession) -> set[str]:
    rows = await db_session.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'"))
    return {r[0] for r in rows}


async def _column_names(db_session: AsyncSession, table: str) -> set[str]:
    rows = await db_session.execute(text(f"PRAGMA table_info({table})"))
    return {r[1] for r in rows}


async def test_the_three_new_tables_exist(db_session: AsyncSession) -> None:
    tables = await _table_names(db_session)
    assert {"coach_invitations", "availability_slots", "impersonation_sessions"} <= tables


async def test_the_six_new_columns_exist(db_session: AsyncSession) -> None:
    assert "trainer_user_id" in await _column_names(db_session, "coach_details")
    assert "joined_at" in await _column_names(db_session, "coach_details")
    assert "availability_updated_at" in await _column_names(db_session, "coach_details")
    assert "availability_updated_at" in await _column_names(db_session, "player_profiles")
    assert "impersonation_id" in await _column_names(db_session, "sessions")
    assert "impersonator_user_id" in await _column_names(db_session, "audit_entries")


async def test_revision_0004_audit_triggers_survive_the_column_addition(
    db_session: AsyncSession,
) -> None:
    """The trap: op.batch_alter_table on audit_entries would have silently
    dropped these two (research.md R2-17)."""
    triggers = await _trigger_names(db_session)
    assert {"trg_audit_entries_no_update", "trg_audit_entries_no_delete"} <= triggers


async def test_the_two_new_impersonation_triggers_exist(db_session: AsyncSession) -> None:
    triggers = await _trigger_names(db_session)
    assert {
        "trg_impersonation_sessions_no_delete",
        "trg_impersonation_sessions_no_update_closed",
    } <= triggers


async def test_downgrade_then_upgrade_round_trips_cleanly(db_session: AsyncSession) -> None:
    """quickstart.md §1's round-trip check, run against the same
    file-backed database `db_session` already migrated to head."""
    import asyncio

    from alembic import command
    from alembic.config import Config

    from app.core.config import get_settings

    alembic_cfg = Config(str(_ALEMBIC_INI_PATH))
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().database_url)

    # The fixture's own AsyncSession must not hold the file open across a
    # schema change made through a second, synchronous connection.
    await db_session.close()

    await asyncio.to_thread(command.downgrade, alembic_cfg, "-1")
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

    # Re-open a session against the now-round-tripped file to assert the
    # schema landed exactly as it did the first time.
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as conn:
        tables = {
            r[0]
            for r in (await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")))
        }
        triggers = {
            r[0]
            for r in (
                await conn.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'"))
            )
        }
    await engine.dispose()

    assert {"coach_invitations", "availability_slots", "impersonation_sessions"} <= tables
    assert {"trg_audit_entries_no_update", "trg_audit_entries_no_delete"} <= triggers
    assert {
        "trg_impersonation_sessions_no_delete",
        "trg_impersonation_sessions_no_update_closed",
    } <= triggers
