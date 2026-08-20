from app.core.errors import RateLimited


def check_rate_limit(*, recent_failure_count: int, max_attempts: int, window_minutes: int) -> None:
    """Pure decision, decoupled from persistence so it is unit-testable
    without a database (FR-013, SC-011).

    The window itself slides because `recent_failure_count` is always a
    count over a trailing window recomputed at call time — once enough
    time passes, the failing attempts fall out of that window and this
    function naturally allows the request again. No administrative unlock
    is ever required.
    """
    if recent_failure_count >= max_attempts:
        raise RateLimited(
            "Too many attempts. Try again in a few minutes.",
            retry_after_seconds=window_minutes * 60,
        )
