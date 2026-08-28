import re
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.errors import ValidationFailure
from app.core.phone import normalize_phone
from app.db.base import utcnow
from app.models.enums import Gender, PlayerProfileKind
from app.schemas.branding import PortalBranding

# Same reservation as CreateUserRequest (FR-076, data-model.md §10).
_ERASURE_PLACEHOLDER_PATTERN = re.compile(r"^deleted_[0-9a-f-]{36}@example\.com$", re.IGNORECASE)


def _age_on(dob: date, *, today: date) -> int:
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


class JoinLinkPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trainer_display_name: str
    branding: PortalBranding
    viewer: "JoinLinkPreviewViewer"


class JoinSelectableProfile(BaseModel):
    """One family member offered on the "who will train with this
    trainer?" question (FR-122, Story 13)."""

    model_config = ConfigDict(extra="forbid")

    player_profile_id: str
    display_name: str
    kind: PlayerProfileKind
    already_associated: bool


class JoinLinkPreviewViewer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # anonymous | can_join | choose_family_members | already_associated
    # | role_cannot_join | child_must_ask_parent
    state: str
    # Present only for `choose_family_members` (FR-122, Story 13).
    selectable_profiles: list[JoinSelectableProfile] | None = None


JoinLinkPreview.model_rebuild()


class JoinAcceptRequest(BaseModel):
    """Which family members join the link's trainer (FR-122, Story 13).
    Omitted or empty `player_profile_ids` associates nobody and changes
    nothing, except for an account holding exactly one live profile,
    which uses it — the 1.1.0 behaviour, preserved (Story 13 scenarios
    3-4)."""

    model_config = ConfigDict(extra="forbid")

    player_profile_ids: list[str] = Field(default_factory=list)


class JoinRegistrationRequest(BaseModel):
    """One account, one player (FR-074). `is_self` selects which age band
    FR-077 applies; `date_of_birth` rather than a literal age, since the
    age is derived and does not decay (research.md R-31)."""

    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    phone: str = Field(min_length=1, max_length=32)
    is_self: bool
    player_name: str | None = Field(default=None, min_length=1, max_length=200)
    date_of_birth: date
    gender: Gender

    @field_validator("email")
    @classmethod
    def _email_not_a_reserved_placeholder(cls, value: str) -> str:
        if _ERASURE_PLACEHOLDER_PATTERN.match(value):
            raise ValueError("This email address format is reserved and cannot be used.")
        return value

    @field_validator("phone")
    @classmethod
    def _phone_is_valid_e164(cls, value: str) -> str:
        try:
            return normalize_phone(value)
        except ValidationFailure as exc:
            raise ValueError(exc.fields.get("phone", exc.message)) from exc

    @model_validator(mode="after")
    def _player_name_matches_is_self(self) -> "JoinRegistrationRequest":
        if self.is_self and self.player_name is not None:
            raise ValueError("player_name must be omitted when the account holder is the player.")
        if not self.is_self and self.player_name is None:
            raise ValueError(
                "player_name is required when registering someone other than yourself."
            )
        return self

    @model_validator(mode="after")
    def _age_matches_is_self(self) -> "JoinRegistrationRequest":
        age = _age_on(self.date_of_birth, today=utcnow().date())
        if self.is_self and age < 18:
            raise ValueError("You must be 18 or older to register yourself as the player.")
        if not self.is_self and not (1 <= age <= 18):
            raise ValueError("A dependant player's age must be between 1 and 18.")
        return self


class JoinResult(BaseModel):
    """**Changed in 1.2.0** (Story 13): a single join may associate
    several family members, so the result reports sets rather than one
    boolean."""

    model_config = ConfigDict(extra="forbid")

    trainer_id: str
    trainer_display_name: str
    associated_profile_ids: list[str]
    already_associated_profile_ids: list[str]
    active_player_profile_id: str | None
    active_trainer_id: str | None
