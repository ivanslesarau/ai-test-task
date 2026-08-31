from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.availability_rules import (
    DAYS_IN_WEEK,
    MAX_SLOTS_PER_DAY,
    MINUTES_IN_DAY,
    MINUTES_PER_SLOT_STEP,
)


class AvailabilitySlotModel(BaseModel):
    """One range on one day (contracts/openapi.yaml `AvailabilitySlot`,
    data-model.md §103). Field bounds and the 15-minute step are encoded
    here as Pydantic constraints, mirroring the openapi schema's
    `minimum`/`maximum`/`multipleOf` and the database's own
    `ck_availability_slots_*` CHECKs (Principle II boundary parity) — a
    malformed request is refused before it ever reaches the service.

    The *set*-level rules (FR-027, FR-028: no overlap, at most six a day)
    are NOT expressible per-slot, so they live in
    `AvailabilityService.validate_week` instead (data-model.md §111.2).
    """

    model_config = ConfigDict(extra="forbid")

    day_of_week: int = Field(ge=0, le=DAYS_IN_WEEK - 1, description="0 = Monday … 6 = Sunday.")
    start_minute: int = Field(
        ge=0,
        le=MINUTES_IN_DAY - MINUTES_PER_SLOT_STEP,
        multiple_of=MINUTES_PER_SLOT_STEP,
    )
    end_minute: int = Field(
        ge=MINUTES_PER_SLOT_STEP,
        le=MINUTES_IN_DAY,
        multiple_of=MINUTES_PER_SLOT_STEP,
        description="May be 1440 (midnight). Must be greater than start_minute.",
    )

    @model_validator(mode="after")
    def _check_order(self) -> "AvailabilitySlotModel":
        if self.start_minute >= self.end_minute:
            raise ValueError("start_minute must be before end_minute")
        return self


class AvailabilityWeekOut(BaseModel):
    """`GET`/`PUT` response (contracts/openapi.yaml `AvailabilityWeek`).
    `updated_at` is `null` for "never stated" and non-null with an empty
    `slots` for "deliberately cleared" — the two are never the same fact
    (FR-035, data-model.md §104)."""

    model_config = ConfigDict(extra="forbid")

    slots: list[AvailabilitySlotModel] = Field(max_length=MAX_SLOTS_PER_DAY * DAYS_IN_WEEK)
    updated_at: datetime | None


class AvailabilityWeekUpdate(BaseModel):
    """`PUT` request body (contracts/openapi.yaml `AvailabilityWeekUpdate`).
    A full replacement, never a patch — an absent range is removed
    (FR-029). An empty array is equivalent to `DELETE`."""

    model_config = ConfigDict(extra="forbid")

    slots: list[AvailabilitySlotModel] = Field(max_length=MAX_SLOTS_PER_DAY * DAYS_IN_WEEK)
