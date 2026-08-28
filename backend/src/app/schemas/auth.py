from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.branding import PortalBranding


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CurrentUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    role: str
    status: str
    first_name: str
    last_name: str
    photo_url: str | None
    # Extension (2026-08-27, family accounts, contract v1.2.0): the pair
    # is now a profile and a trainer together (FR-117), `trainer_count`
    # becomes `context_count` (research.md R-49), and `is_child_account`
    # is derived (research.md R-38).
    active_player_profile_id: str | None
    active_trainer_id: str | None
    context_count: int
    is_child_account: bool
    portal_branding: PortalBranding


class InvitationCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_hint: str
    expires_at: datetime


class SetupPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=1, max_length=128)
