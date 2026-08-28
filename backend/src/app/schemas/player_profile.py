from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.family_rules import age_on, is_valid_age_for_kind
from app.db.base import utcnow
from app.models.enums import Gender, PlayerProfileKind


class PlayerProfileAssociation(BaseModel):
    """One trainer a player profile trains with (FR-124). Addressed for
    removal by `association_id`, never by `trainer_id` (research.md
    R-48)."""

    model_config = ConfigDict(extra="forbid")

    association_id: str
    trainer_id: str
    trainer_display_name: str
    joined_at: datetime


class PlayerProfile(BaseModel):
    """One player on the account (FR-106, FR-107). Replaces the per-player
    fields `PlayerParentDetail` carried before contract v1.2.0
    (research.md R-34)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: PlayerProfileKind
    display_name: str
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    age: int | None = None
    gender: str | None = None
    school: str | None = None
    jersey_number: str | None = None
    skill_level: str | None = None
    photo_url: str | None = None
    tokens_without_approval: bool
    has_sign_in: bool
    associations: list[PlayerProfileAssociation] = Field(default_factory=list)


class PlayerProfileList(BaseModel):
    """Every live profile on the account, unpaged (FR-124). A signed-in
    child receives exactly one entry (FR-132)."""

    model_config = ConfigDict(extra="forbid")

    profiles: list[PlayerProfile]


class CreateChildProfileRequest(BaseModel):
    """Creates a `child` profile (FR-107). `kind` is not a field — this
    endpoint creates children only; the account holder's own profile is
    created at registration."""

    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    gender: Gender
    school: str | None = Field(default=None, min_length=1, max_length=200)
    jersey_number: str | None = Field(default=None, min_length=1, max_length=10)
    trainer_ids: list[str] = Field(default_factory=list)
    acknowledge_possible_duplicate: bool = False

    @model_validator(mode="after")
    def _age_is_within_the_child_band(self) -> "CreateChildProfileRequest":
        age = age_on(self.date_of_birth, today=utcnow().date())
        if not is_valid_age_for_kind(PlayerProfileKind.CHILD, age):
            raise ValueError("A child's age must be between 1 and 18.")
        return self


class PlayerProfileUpdate(BaseModel):
    """Every field optional — a partial update. An omitted key leaves its
    stored value untouched; a key present with `null` clears it, except
    for `first_name`/`last_name`, which map to columns that are NOT NULL
    on a `child` profile and absent-by-design on a `self` one — an
    explicit `null` for either is rejected here, and presence of either on
    a `self` profile is rejected by `family_service` (research.md R-37,
    constitution Principle VI)."""

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: Gender | None = None
    school: str | None = Field(default=None, min_length=1, max_length=200)
    jersey_number: str | None = Field(default=None, min_length=1, max_length=10)
    tokens_without_approval: bool | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _reject_explicit_null_names(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be cleared.")
        return value

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def _reject_explicit_null_date_of_birth(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be cleared.")
        return value

    @field_validator("gender", mode="before")
    @classmethod
    def _reject_explicit_null_gender(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be cleared.")
        return value

    @field_validator("tokens_without_approval", mode="before")
    @classmethod
    def _reject_explicit_null_tokens_without_approval(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be cleared.")
        return value


class DuplicateProfileErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = "possible_duplicate_profile"
    message: str
    matches: list[PlayerProfile]


class DuplicateProfileError(BaseModel):
    """The 409 body a near-duplicate child produces (FR-110, research.md
    R-45), carrying what matched so the parent can see whether they meant
    it."""

    model_config = ConfigDict(extra="forbid")

    error: DuplicateProfileErrorBody


class AddPlayerTrainerRequest(BaseModel):
    """Exactly one of `code` or `trainer_id` must be present — FR-125's
    two ways in. The `.refine`-equivalent lives on the object, not on
    either field, because the rule is about the pair."""

    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=8, max_length=64)
    trainer_id: str | None = None

    @model_validator(mode="after")
    def _exactly_one_of_code_or_trainer_id(self) -> "AddPlayerTrainerRequest":
        if (self.code is None) == (self.trainer_id is None):
            raise ValueError("Supply exactly one of code or trainer_id.")
        return self
