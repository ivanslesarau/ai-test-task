from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import PlayerProfileKind


class ResponsibleContact(BaseModel):
    """The adult a trainer contacts about a player (contract v1.2.0,
    FR-113, FR-116). Never carries the responsible account's identifier,
    so a roster row cannot be used to correlate siblings across two
    trainers' rosters (SC-040)."""

    model_config = ConfigDict(extra="forbid")

    display_name: str
    email: str | None
    phone: str | None


class TrainerPlayerSummary(BaseModel):
    """One row of a trainer's roster. Deliberately carries nothing about
    the player's other trainers (FR-090, SC-025) and nothing about any
    other profile on the same account (FR-116, SC-040).

    **Changed in 1.2.0** (data-model.md §35, research.md R-49): names a
    player profile rather than an account — `player_user_id` is gone —
    and carries the responsible adult's contact detail, since a trainer
    with a child on their roster must be able to reach the parent."""

    model_config = ConfigDict(extra="forbid")

    player_profile_id: str
    display_name: str
    kind: PlayerProfileKind
    age: int | None
    gender: str | None
    joined_at: datetime
    photo_url: str | None
    responsible_contact: ResponsibleContact


class TrainerPlayerPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TrainerPlayerSummary]
    page: int
    page_size: int
    total: int
