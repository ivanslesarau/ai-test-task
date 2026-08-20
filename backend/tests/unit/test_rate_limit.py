import pytest

from app.core.errors import RateLimited
from app.core.rate_limit import check_rate_limit


def test_allows_when_under_the_limit() -> None:
    check_rate_limit(recent_failure_count=9, max_attempts=10, window_minutes=15)


def test_blocks_at_the_limit() -> None:
    with pytest.raises(RateLimited) as exc_info:
        check_rate_limit(recent_failure_count=10, max_attempts=10, window_minutes=15)
    assert exc_info.value.retry_after_seconds == 15 * 60


def test_blocks_above_the_limit() -> None:
    with pytest.raises(RateLimited):
        check_rate_limit(recent_failure_count=50, max_attempts=10, window_minutes=15)


def test_recovery_is_automatic_once_the_window_has_no_recent_failures() -> None:
    """The window sliding out of failures — not an administrative unlock —
    is what restores access (SC-011). Here that's modeled by the caller
    recomputing a lower count once older failures fall outside the
    window; this function has no memory between calls to defeat."""
    check_rate_limit(recent_failure_count=0, max_attempts=10, window_minutes=15)
