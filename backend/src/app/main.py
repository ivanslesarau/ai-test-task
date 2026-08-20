import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import admin_users_router, auth_router, me_router, media_router
from app.core.config import get_settings
from app.core.errors import (
    AccountNotActive,
    ActionNotPermitted,
    Conflict,
    InvalidCredentials,
    InvitationNotUsable,
    NotAuthenticated,
    NotFound,
    PayloadTooLarge,
    PermissionDenied,
    RateLimited,
    StaleVersion,
    UnsupportedMediaType,
    ValidationFailure,
)
from app.core.logging import configure_logging, register_request_logging
from app.schemas.common import (
    Error,
    ErrorBody,
    FieldError,
    ValidationErrorBody,
    ValidationErrorResponse,
)

logger = logging.getLogger("app")


def _error(code: str, message: str) -> dict:
    return Error(error=ErrorBody(code=code, message=message)).model_dump()


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="PracticePerfect API", version="1.0.0")

    register_request_logging(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_base_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Exception handlers -------------------------------------------------
    # Every domain error maps to exactly one status code and the single
    # Error envelope (FR-056). The catch-all logs full detail server-side
    # and returns a generic body — no stack trace, driver message, or
    # credential material ever reaches a client (SC-012).

    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content=_error("not_found", exc.message))

    @app.exception_handler(PermissionDenied)
    async def _permission_denied(_: Request, exc: PermissionDenied) -> JSONResponse:
        return JSONResponse(status_code=403, content=_error("forbidden", exc.message))

    @app.exception_handler(InvalidCredentials)
    async def _invalid_credentials(_: Request, exc: InvalidCredentials) -> JSONResponse:
        return JSONResponse(status_code=401, content=_error("invalid_credentials", exc.message))

    @app.exception_handler(NotAuthenticated)
    async def _not_authenticated(_: Request, exc: NotAuthenticated) -> JSONResponse:
        return JSONResponse(status_code=401, content=_error("not_authenticated", exc.message))

    @app.exception_handler(AccountNotActive)
    async def _account_not_active(_: Request, exc: AccountNotActive) -> JSONResponse:
        return JSONResponse(status_code=403, content=_error("account_not_active", exc.message))

    @app.exception_handler(InvitationNotUsable)
    async def _invitation_not_usable(_: Request, exc: InvitationNotUsable) -> JSONResponse:
        return JSONResponse(status_code=410, content=_error("invitation_not_usable", exc.message))

    @app.exception_handler(Conflict)
    async def _conflict(_: Request, exc: Conflict) -> JSONResponse:
        return JSONResponse(
            status_code=409, content=_error("email_already_registered", exc.message)
        )

    @app.exception_handler(StaleVersion)
    async def _stale_version(_: Request, exc: StaleVersion) -> JSONResponse:
        return JSONResponse(status_code=409, content=_error("stale_version", exc.message))

    @app.exception_handler(ActionNotPermitted)
    async def _action_not_permitted(_: Request, exc: ActionNotPermitted) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error(exc.code, exc.message))

    @app.exception_handler(ValidationFailure)
    async def _validation_failure(_: Request, exc: ValidationFailure) -> JSONResponse:
        body = ValidationErrorResponse(
            error=ValidationErrorBody(
                message=exc.message,
                fields=[FieldError(field=k, message=v) for k, v in exc.fields.items()],
            )
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(PayloadTooLarge)
    async def _payload_too_large(_: Request, exc: PayloadTooLarge) -> JSONResponse:
        return JSONResponse(status_code=413, content=_error("payload_too_large", exc.message))

    @app.exception_handler(UnsupportedMediaType)
    async def _unsupported_media_type(_: Request, exc: UnsupportedMediaType) -> JSONResponse:
        return JSONResponse(status_code=415, content=_error("unsupported_image", exc.message))

    @app.exception_handler(RequestValidationError)
    async def _request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Pydantic-level request parsing errors (malformed email, missing
        required field, ...) go through this handler instead of FastAPI's
        default `{"detail": [...]}` shape, so every 422 in the API uses
        the one Error envelope (FR-022: each offending field identified
        individually, in the contract's shape)."""
        fields = [
            FieldError(
                field=".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path")),
                message=err["msg"],
            )
            for err in exc.errors()
        ]
        body = ValidationErrorResponse(
            error=ValidationErrorBody(message="One or more fields are invalid.", fields=fields)
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(RateLimited)
    async def _rate_limited(_: Request, exc: RateLimited) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content=_error("too_many_attempts", exc.message),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error("internal_error", "Something went wrong. Please try again."),
        )

    app.include_router(auth_router.router, prefix="/api/v1")
    app.include_router(me_router.router, prefix="/api/v1")
    app.include_router(admin_users_router.router, prefix="/api/v1")
    app.include_router(media_router.router, prefix="/api/v1")

    return app


app = create_app()
