import asyncio
import os
import uuid
from collections.abc import AsyncGenerator, Callable
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Environment must be set before app.core.config.get_settings() is ever
# called (including transitively via app.main import), since Settings has
# no defaults for these fields by design.
_TEST_ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "SESSION_COOKIE_NAME": "pp_session",
    "SESSION_IDLE_DAYS": "7",
    "INVITATION_TTL_HOURS": "24",
    "SIGNIN_MAX_ATTEMPTS": "10",
    "SIGNIN_WINDOW_MINUTES": "15",
    "UPLOAD_DIR": "./var/test-uploads",
    "MAX_UPLOAD_BYTES": "5242880",
    "EMAIL_BACKEND": "filesystem",
    "EMAIL_OUTBOX_DIR": "./var/test-outbox",
    "FRONTEND_BASE_URL": "http://localhost:5173",
    "BOOTSTRAP_ADMIN_EMAIL": "bootstrap-admin@example.org",
    "BOOTSTRAP_ADMIN_PASSWORD": "bootstrap-password-123456",
    "COACH_INVITATION_TTL_DAYS": "7",
    "IMPERSONATION_MAX_MINUTES": "60",
}
for key, value in _TEST_ENV.items():
    os.environ.setdefault(key, value)

_ALEMBIC_INI_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """A fresh, migrated, file-backed SQLite database per test.

    File-backed (not :memory:) because pragmas and cross-connection
    behavior should match production; a unique file per test keeps tests
    isolated without needing to reset state between them.
    """
    from alembic import command
    from alembic.config import Config

    from app.db.base import Base

    db_path = Path("var") / f"test-{uuid.uuid4().hex}.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    database_url = f"sqlite+aiosqlite:///{db_path}"

    os.environ["DATABASE_URL"] = database_url
    from app.core.config import get_settings
    from app.db.engine import get_engine

    get_settings.cache_clear()
    # get_engine() is process-wide @lru_cache'd; without clearing it here,
    # a test that exercises the real get_db_session dependency (rather
    # than overriding it) would silently keep talking to whichever
    # database file the first such test happened to create.
    get_engine.cache_clear()

    alembic_cfg = Config(str(_ALEMBIC_INI_PATH))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

    engine = create_async_engine(database_url)
    from sqlalchemy import event

    from app.db.engine import _set_sqlite_pragmas

    event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session

    await engine.dispose()
    await get_engine().dispose()
    get_engine.cache_clear()

    def _cleanup() -> None:
        db_path.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(str(db_path) + suffix).unlink(missing_ok=True)

    await asyncio.to_thread(_cleanup)

    _ = Base  # imported for its side effect of registering all models


@pytest.fixture
async def app_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """An httpx client over the real ASGI app, with the database dependency
    overridden to the per-test session so every request in a test shares
    one transaction-free connection and one migrated schema."""
    from app.db.session import get_db_session
    from app.main import app

    async def _override() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def real_app_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Like `app_client`, but does NOT override `get_db_session` — requests
    go through the actual per-request commit/rollback logic in
    app/db/session.py instead of the test's manually-managed session.

    Use this specifically to test that transaction boundary itself (e.g.
    that a DomainError still commits writes made before it was raised).
    Prefer `app_client` for everything else; it's cheaper and lets a test
    both make requests and inspect state through the same session.
    """
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as client:
        yield client

    _ = db_session  # depended on only to ensure the schema is migrated


@pytest.fixture
def authenticated_client_factory(
    app_client: AsyncClient,
) -> Callable[[str], AsyncClient]:
    """Returns a function that signs the given account's cookie onto
    app_client, letting tests act as one of several roles without spinning
    up a second client per role."""

    def _factory(session_cookie_value: str) -> AsyncClient:
        app_client.cookies.set("pp_session", session_cookie_value)
        return app_client

    return _factory
