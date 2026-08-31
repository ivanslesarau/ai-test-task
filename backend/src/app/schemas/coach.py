from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.availability import AvailabilitySlotModel
from app.schemas.branding import PortalBranding

# The canonical `CoachSummary` (tasks.md T550, contracts/openapi.yaml
# `CoachSummary`). `schemas/coach_invitation.py` defined a stopgap,
# identically-shaped copy for User Story 1 (its own docstring flagged this
# as a decision point) because this module did not exist yet — that copy
# is now deleted and `CoachInvitationOut.coach` imports this one instead,
# so exactly one `CoachSummary` exists in the codebase.


class CoachSummary(BaseModel):
    """Matches contracts/openapi.yaml `CoachSummary`."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    first_name: str
    last_name: str
    email: EmailStr
    status: Literal["active", "inactive", "deleted"]
    photo_url: str | None


class TrainerCoachSummary(CoachSummary):
    """Matches contracts/openapi.yaml `TrainerCoachSummary` (`allOf`
    `CoachSummary`). Carries the coach's stated week inline so a roster
    page renders its "Best times" summary without one request per row
    (research.md R2-12) — `availability` is populated by one `IN` query
    for the whole page, never one query per coach (data-model.md §113)."""

    model_config = ConfigDict(extra="forbid")

    joined_at: datetime
    availability: list[AvailabilitySlotModel]
    availability_updated_at: datetime | None


class TrainerCoachPage(BaseModel):
    """Matches contracts/openapi.yaml `TrainerCoachPage`."""

    model_config = ConfigDict(extra="forbid")

    items: list[TrainerCoachSummary]
    total: int
    page: int
    page_size: int


class CoachInvitationPreviewTrainer(BaseModel):
    """The inline `trainer` object of contracts/openapi.yaml
    `CoachInvitationPreview` — the trainer's public identity only: no
    address, no contact detail, no counts."""

    model_config = ConfigDict(extra="forbid")

    business_name: str
    portal_branding: PortalBranding


class CoachInvitationPreview(BaseModel):
    """Matches contracts/openapi.yaml `CoachInvitationPreview`. Public and
    unauthenticated (`GET /coach-invitations/{token}`, `security: []`) —
    gated on possession of the mailed 256-bit token, not on a session
    (research.md R2-05)."""

    model_config = ConfigDict(extra="forbid")

    invited_email: EmailStr
    invitee_name: str | None
    message: str | None
    expires_at: datetime
    account_exists: bool
    trainer: CoachInvitationPreviewTrainer


class CoachRegistrationRequest(BaseModel):
    """Matches contracts/openapi.yaml `CoachRegistrationRequest`. No
    `email`, `role`, or `trainer_id` — all three are taken from the
    invitation itself (FR-011, FR-013), so a malicious body naming a
    different address, role, or trainer has nothing to act on."""

    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    bio: str | None = Field(default=None, min_length=1, max_length=2000)
    credentials: str | None = Field(default=None, min_length=1, max_length=1000)
    certifications: str | None = Field(default=None, min_length=1, max_length=1000)


class CoachJoinResult(BaseModel):
    """Matches contracts/openapi.yaml `CoachJoinResult`. FR-016's no-op
    re-acceptance is reported as an `outcome`, not as an error."""

    model_config = ConfigDict(extra="forbid")

    outcome: Literal["joined", "already_on_this_roster"]
    trainer_business_name: str
    joined_at: datetime
