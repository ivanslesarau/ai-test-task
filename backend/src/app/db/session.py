from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.db.engine import get_sessionmaker


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Per-request session, injected via Depends.

    A `DomainError` (wrong password, permission denied, ...) is an
    anticipated business outcome, not a failure of the transaction — the
    request still commits, so writes made before the error was raised
    (a failed-attempt row for rate limiting, a `permission_denied` audit
    entry) are persisted even though the response is a 4xx. Only a
    genuinely unexpected exception rolls the transaction back.
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
        except DomainError:
            await session.commit()
            raise
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
