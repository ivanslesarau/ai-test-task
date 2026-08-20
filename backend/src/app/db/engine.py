from functools import lru_cache
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import ConnectionPoolEntry

from app.core.config import get_settings


def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: ConnectionPoolEntry) -> None:
    """Enable foreign keys and WAL mode on every new SQLite connection.

    SQLite does not enforce foreign keys unless told to per connection, and
    the erasure design (data-model.md §8-9) depends on those keys holding
    history to accounts. WAL lets the read-heavy directory proceed during
    administrative writes. PRAGMA is not expressible as an ORM or Core
    construct — this is the first of the two documented raw-SQL exceptions
    in plan.md §Complexity Tracking. Parameterless, no user input, confined
    to this one function.

    The stack is SQLite-only (constitution: fixed stack), so this always
    receives aiosqlite's AsyncAdapt_aiosqlite_connection, which exposes the
    same synchronous cursor() interface as stdlib sqlite3.Connection for use
    inside pool-level connect events.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)
    return engine


def get_sessionmaker() -> async_sessionmaker:
    return async_sessionmaker(get_engine(), expire_on_commit=False)
