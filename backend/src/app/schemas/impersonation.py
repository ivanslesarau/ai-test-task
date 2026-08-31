from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImpersonationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str


class ImpersonationParticipant(BaseModel):
    """Named by identifier first (contracts/openapi.yaml `Impersonation
    Participant`): after the impersonated account is erased, `display_name`
    is the anonymized name feature 001's erasure leaves behind, and the
    entry still stands (FR-055)."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    display_name: str
    role: str


class ImpersonationOut(BaseModel):
    """Matches `Impersonation` in contracts/openapi.yaml. `duration_seconds`
    is computed by the service from the two timestamps and is `null` while
    the impersonation is still in progress (research.md R2-18)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    admin: ImpersonationParticipant
    target: ImpersonationParticipant
    target_status_at_start: str
    started_at: datetime
    expires_at: datetime
    ended_at: datetime | None
    end_reason: str | None
    duration_seconds: int | None


class ImpersonationPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ImpersonationOut]
    total: int
    page: int
    page_size: int
