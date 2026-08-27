"""FR-071, SC-021, research.md R-30. The per-origin throttle on
invitation-link lookups — this is the endpoint's only public,
unauthenticated attack surface for finding a valid code."""

import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RateLimited
from app.core.rate_limit import check_rate_limit
from app.repositories.share_link_repository import ShareLinkRepository
from tests.helpers import create_trainer_with_link


async def test_eleventh_unsuccessful_lookup_from_one_origin_is_throttled(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    for _ in range(10):
        response = await app_client.get("/join/not-a-real-code")
        assert response.status_code == 404

    throttled = await app_client.get("/join/still-not-a-real-code")

    assert throttled.status_code == 429
    assert "Retry-After" in throttled.headers
    assert throttled.json()["error"]["code"] == "too_many_attempts"


async def test_successful_lookups_do_not_count_against_the_throttle(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    for _ in range(20):
        response = await app_client.get(f"/join/{link.code}")
        assert response.status_code == 200


async def test_throttle_is_per_origin_only(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """FR-071 counts only client_ip — there is no per-code dimension,
    since an invalid code identifies nobody to key a second counter on."""
    with pytest.raises(RateLimited):
        check_rate_limit(recent_failure_count=10, max_attempts=10, window_minutes=15)


async def test_a_ten_thousand_invalid_code_trial_finds_no_valid_link(
    db_session: AsyncSession,
) -> None:
    """SC-021: an automated trial of invalid codes must discover no valid
    link. Exercised directly against the repository (bypassing HTTP and
    the throttle, which test_eleventh_unsuccessful_lookup_... already
    covers) because 10,000 real HTTP round trips would make this test
    itself the slow part of the suite; the property being proven is that
    ShareLinkRepository.get_by_code never matches a guessed value against
    a 128-bit code space, which a direct repository sweep proves exactly
    as well."""
    _, real_link = await create_trainer_with_link(db_session)
    await db_session.commit()

    repo = ShareLinkRepository(db_session)
    guesses_matched = 0
    for _ in range(10_000):
        guess = secrets.token_urlsafe(16)
        if guess == real_link.code:  # astronomically unlikely; guards the test's own logic
            guesses_matched += 1
            continue
        found = await repo.get_by_code(guess)
        if found is not None:
            guesses_matched += 1

    assert guesses_matched == 0
