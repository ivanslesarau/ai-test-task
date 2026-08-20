from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import utcnow
from app.models.auth import SignInAttempt
from app.models.enums import UserRole
from tests.helpers import create_user


async def test_refuses_after_the_configured_number_of_failures(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()
    settings = get_settings()

    # quickstart.md §4 scenario 1.7: the first `signin_max_attempts` failures
    # are each refused as ordinary wrong-credential 401s; only the attempt
    # *after* the limit has been reached is rate-limited.
    responses = []
    for _ in range(settings.signin_max_attempts + 1):
        responses.append(
            await app_client.post(
                "/auth/login", json={"email": user.email, "password": "wrong-password-attempt"}
            )
        )

    assert [r.status_code for r in responses[:-1]] == [401] * settings.signin_max_attempts
    assert responses[-1].status_code == 429
    assert "Retry-After" in responses[-1].headers


async def test_admits_again_automatically_once_the_window_has_passed(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """SC-011: recovery is automatic — no administrative unlock. Modeled
    here by inserting failure rows already outside the window, rather
    than sleeping in the test."""
    user = await create_user(db_session, role=UserRole.TRAINER)
    settings = get_settings()
    stale_time = utcnow() - timedelta(minutes=settings.signin_window_minutes + 5)

    # ASGITransport's default synthetic client address (httpx docs / source:
    # ASGITransport.__init__ defaults `client=("127.0.0.1", 123)`), which is
    # what request.client.host resolves to for every request in this suite.
    for _ in range(settings.signin_max_attempts + 5):
        db_session.add(
            SignInAttempt(
                email=user.email,
                client_ip="127.0.0.1",
                attempted_at=stale_time,
                successful=False,
            )
        )
    await db_session.commit()

    from tests.helpers import KNOWN_PASSWORD

    response = await app_client.post(
        "/auth/login", json={"email": user.email, "password": KNOWN_PASSWORD}
    )

    assert response.status_code == 200


async def test_a_failed_attempt_is_persisted_despite_the_401_response(
    real_app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Regression test: a request that ends in a DomainError (here,
    InvalidCredentials) must still commit the writes it made before
    raising — specifically, the failed-attempt row this whole rate limit
    depends on. Uses `real_app_client` deliberately, because `app_client`'s
    dependency override bypasses the real per-request commit/rollback path
    in app/db/session.py and would not have caught this."""
    user = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()

    response = await real_app_client.post(
        "/auth/login", json={"email": user.email, "password": "wrong-password-value"}
    )
    assert response.status_code == 401

    rows = (
        (await db_session.execute(select(SignInAttempt).where(SignInAttempt.email == user.email)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].successful is False
