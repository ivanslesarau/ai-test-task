"""Domain error hierarchy.

No HTTP or SQLAlchemy imports here — services raise these, and the HTTP
layer (main.py exception handlers) is the only place that knows how to turn
one into a status code and response body. Keeping services framework-free
is what Principle III (layered architecture) requires: the service layer
must not depend on transport concerns.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base for every error a service may raise."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFound(DomainError):
    pass


class PermissionDenied(DomainError):
    pass


class Conflict(DomainError):
    """A request conflicts with the current state (e.g. duplicate email)."""


class StaleVersion(DomainError):
    """The caller's observed `version` no longer matches (R-10)."""


class ValidationFailure(DomainError):
    """One or more fields are invalid. `fields` maps field name to message."""

    def __init__(self, message: str, fields: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.fields = fields or {}


class RateLimited(DomainError):
    """Too many recent failed sign-in attempts (FR-013, SC-011)."""

    def __init__(self, message: str, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class InvalidCredentials(DomainError):
    """Unknown email, wrong password, or no password set yet — all
    indistinguishable to the caller (FR-010)."""


class NotAuthenticated(DomainError):
    """No session cookie, or the session is expired/revoked/for a
    non-Active account (FR-018)."""


class AccountNotActive(DomainError):
    """Credentials were correct but the account is not Active."""


class InvitationNotUsable(DomainError):
    """A setup link that is consumed, expired, superseded, or whose account
    is not Active (FR-027)."""


class ActionNotPermitted(DomainError):
    """A status-change action that is not valid for the target's current
    state or context — e.g. self-action, last active Super Admin, wrong
    starting status (FR-041, FR-048)."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


class PayloadTooLarge(DomainError):
    """An uploaded file exceeds the configured size limit (FR-034)."""


class UnsupportedMediaType(DomainError):
    """An uploaded file did not decode as one of the accepted image
    formats (FR-034, R-07)."""
