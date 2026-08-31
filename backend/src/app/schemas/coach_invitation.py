from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.coach_invitation import CoachInvitation as CoachInvitationModel
from app.schemas.coach import CoachSummary

# The **presented** state (data-model.md §101.1). `superseded` is
# deliberately absent — a superseded row is never returned to a client,
# because a resend leaves one live invitation per address, not two
# (FR-005). `CoachInvitationService.presented_state` computes a broader,
# six-value internal type that includes `superseded` for testability
# (tasks.md T517); this narrower one is what the contract allows out.
CoachInvitationPresentedState = Literal["awaiting", "accepted", "expired", "revoked", "blocked"]

CoachInvitationBlockReasonValue = Literal["role_not_coach", "already_assigned"]


class CoachInvitationCreate(BaseModel):
    """Matches contracts/openapi.yaml `CoachInvitationCreate`. `invitee_name`
    and `message` are `str | None` with `min_length=1`, so an empty string
    is a 422 rather than a stored `""` (constitution Principle VI,
    data-model.md §111.1)."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    invitee_name: str | None = Field(default=None, min_length=1, max_length=200)
    message: str | None = Field(default=None, min_length=1, max_length=2000)


class CoachInvitationOut(BaseModel):
    """Matches contracts/openapi.yaml `CoachInvitation`. `state` is always
    the *presented* state (data-model.md §101.1) — never the raw stored
    `state` column value for the `expired`/`blocked` cases, and never
    `superseded` (those rows are not returned)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    invited_email: EmailStr
    invitee_name: str | None
    message: str | None
    state: CoachInvitationPresentedState
    issued_at: datetime
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    blocked_reason: CoachInvitationBlockReasonValue | None
    coach: CoachSummary | None


class CoachInvitationPage(BaseModel):
    """Matches contracts/openapi.yaml `CoachInvitationPage`."""

    model_config = ConfigDict(extra="forbid")

    items: list[CoachInvitationOut]
    total: int
    page: int
    page_size: int


def build_coach_invitation_out(
    invitation: CoachInvitationModel,
    *,
    presented_state: CoachInvitationPresentedState,
    coach: CoachSummary | None = None,
) -> CoachInvitationOut:
    """The one mapper from the ORM row to the wire shape, mirroring
    `schemas/share_link.py`'s `build_share_link_out` pattern. `coach`
    defaults to `None` because User Story 1 never has one to pass — kept
    as an explicit parameter (rather than derived here) so User Story 2
    can supply a resolved `CoachSummary` without this function's shape
    changing."""
    return CoachInvitationOut(
        id=invitation.id,
        invited_email=invitation.invited_email,
        invitee_name=invitation.invitee_name,
        message=invitation.message,
        state=presented_state,
        issued_at=invitation.issued_at,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        revoked_at=invitation.revoked_at,
        blocked_reason=invitation.blocked_reason,  # type: ignore[arg-type]
        coach=coach,
    )
