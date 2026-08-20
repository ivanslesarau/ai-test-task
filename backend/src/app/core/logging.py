import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("app.request")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def register_request_logging(app: FastAPI) -> None:
    """One structured line per request: method, path, status, duration,
    and the acting account id if the request authenticated — never the
    request body, which may carry a password or other personal data
    (FR-056)."""

    @app.middleware("http")
    async def _log_request(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started_at = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - started_at) * 1000
        actor_id = getattr(request.state, "current_user_id", None)
        logger.info(
            "%s %s -> %d (%.1fms) actor=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            actor_id or "-",
        )
        return response
