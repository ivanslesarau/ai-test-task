from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import PlayerProfileKind
from app.schemas.branding import PortalBranding


class TrainingContextEntry(BaseModel):
    """One switchable pair, replacing `TrainerContextEntry` (research.md
    R-49). Names both halves, because a parent's switcher groups by
    profile and a sibling training with the same trainer is a different
    context (FR-117, FR-118)."""

    model_config = ConfigDict(extra="forbid")

    player_profile_id: str
    player_display_name: str
    player_profile_kind: PlayerProfileKind
    trainer_id: str
    trainer_display_name: str
    branding: PortalBranding
    joined_at: datetime


class TrainingContextList(BaseModel):
    """The switcher's whole state, replacing `TrainerContextList`
    (research.md R-49). `contexts` holds only Active associations with
    Active trainers on live profiles, so every entry is switchable
    (FR-089, FR-120). One entry means no switcher is shown (FR-118,
    FR-119); an empty list means the person belongs to no trainer, which
    is valid.

    For a signed-in child every entry carries the same
    `player_profile_id` — their own — and no sibling appears (FR-119,
    FR-132)."""

    model_config = ConfigDict(extra="forbid")

    active_player_profile_id: str | None
    active_trainer_id: str | None
    contexts: list[TrainingContextEntry]


class TrainingContextRequest(BaseModel):
    """Both halves are required — a trainer alone no longer identifies a
    context (FR-117). Named in the body rather than the path, which is
    what keeps context server-resolved everywhere else (research.md
    R-25, R-48)."""

    model_config = ConfigDict(extra="forbid")

    player_profile_id: str
    trainer_id: str
