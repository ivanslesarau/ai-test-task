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
    # Extension (2026-08-26): multi-trainer context and branding.
    active_trainer_id: str | None
    trainer_count: int
    portal_branding: PortalBranding


class InvitationCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_hint: str
    expires_at: datetime


class SetupPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=1, max_length=128)
