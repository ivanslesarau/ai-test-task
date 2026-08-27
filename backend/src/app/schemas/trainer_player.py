from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrainerPlayerSummary(BaseModel):
    """One row of a trainer's roster. Deliberately carries nothing about
    the player's other trainers (FR-090, SC-025)."""

    model_config = ConfigDict(extra="forbid")

    player_user_id: str
    display_name: str
    is_self: bool
    age: int | None
    gender: str | None
    joined_at: datetime
    photo_url: str | None


class TrainerPlayerPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TrainerPlayerSummary]
    page: int
    page_size: int
    total: int
