from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.branding import PortalBranding


class TrainerContextEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trainer_id: str
    display_name: str
    branding: PortalBranding
    joined_at: datetime


class TrainerContextList(BaseModel):
    """The switcher's whole state (FR-088, FR-089). `trainers` holds only
    Active associations with Active trainers, so every entry is
    switchable. One entry means no switcher is shown; an empty list means
    the person belongs to no trainer, which is valid."""

    model_config = ConfigDict(extra="forbid")

    active_trainer_id: str | None
    trainers: list[TrainerContextEntry]


class TrainerContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trainer_id: str
