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


class InvitationLinkInvalid(DomainError):
    """An invitation link that is unknown, revoked, expired, exhausted, or
    whose owning trainer is not Active (FR-070). One message for all five
    causes — the caller must not be able to tell which applies."""


class RoleCannotJoin(DomainError):
    """A signed-in caller whose role is not Player/Parent attempted to
    join a trainer through a player invitation link (FR-081)."""


# --- Extension (2026-08-27): family accounts, child sign-in, approvals -----


class PlayerProfileNotFound(DomainError):
    """A `player_profiles` id that does not exist, does not belong to the
    caller's account, or — for a signed-in child — belongs to a sibling
    (FR-112, FR-132). One message for all three: a distinction would
    confirm a sibling's profile exists (research.md R-48)."""


class PossibleDuplicateProfile(DomainError):
    """A `POST /me/players` submission matches an existing live profile
    on the same account by date of birth and case-insensitive trimmed
    name (research.md R-45). Carries the matching profiles, already
    serialized to the `PlayerProfile` shape (contract's
    `DuplicateProfileError.error.matches`), so the caller can see what
    matched and re-submit with `acknowledge_possible_duplicate: true`
    (FR-110)."""

    def __init__(self, message: str, matches: list[dict]) -> None:
        super().__init__(message)
        self.matches = matches


class ParentOnlyField(DomainError):
    """A signed-in child attempted to write a field FR-132 reserves for
    the owning parent — e.g. `tokens_without_approval` (FR-132, FR-147).
    Refused on the request, never only by withholding the control
    (FR-133)."""


class ChildMustAskParent(DomainError):
    """A signed-in child attempted an action FR-137 routes through the
    Pending Parent Approval workflow instead — e.g. joining a trainer
    directly. No association is created and nothing about the child's
    account changes; an approval request is raised instead."""


class RequestAlreadyResolved(DomainError):
    """An approval request is no longer live — already approved, denied,
    withdrawn, or lapsed — when a resolution was attempted (FR-156). The
    conditional UPDATE's zero-row result is what raises this (research.md
    R-41); the caller never read the row first."""


class ApprovalSubjectUnavailable(DomainError):
    """The subject of a `join_trainer` approval request is no longer
    reachable at resolution time — the trainer's account is no longer
    Active, or the share link's association already exists (FR-145)."""


class ApprovalKindNotExecutable(DomainError):
    """An approval request of a financial kind (`usd_payment`,
    `token_spend`) was approved before Epic-05 registers an executor for
    it (research.md R-42, R-46). FR-142's last clause: such a request
    must not be marked approved until the action it approves can actually
    be carried out."""


class ApprovalAmountChanged(DomainError):
    """The amount shown to the parent at approval time no longer matches
    the amount recorded on the request (FR-152) — refused rather than
    charging a different figure than the one the parent saw."""
