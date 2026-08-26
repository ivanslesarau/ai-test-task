from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.role_detail import RoleDetailOut


class OwnProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    role: str
    status: str
    created_at: datetime
    first_name: str
    last_name: str
    phone: str | None
    photo_url: str | None
    thumbnail_url: str | None
    role_detail: RoleDetailOut
    editable_fields: list[str]


class OwnProfileUpdate(BaseModel):
    """Every field optional — a partial update. Submitting a field not
    editable for the requester's role is rejected with 422, not silently
    dropped (FR-033) — enforced in ProfileService, not here, since the
    allowed set depends on the requester's role."""

    model_config = ConfigDict(extra="forbid")

    # first_name/last_name map to NOT NULL columns: omitting the key leaves
    # the column untouched, but an *explicit* null must not reach `setattr`
    # (constitution Principle VI) — `_reject_explicit_null_names` below
    # rejects that case with a field-attributed 422 before Pydantic's own
    # `min_length` check ever runs against `None`.
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    business_name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    website: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    bio: str | None = Field(default=None, min_length=1, max_length=2000)
    credentials: str | None = Field(default=None, min_length=1, max_length=1000)
    certifications: str | None = Field(default=None, min_length=1, max_length=1000)
    is_publicly_visible: bool | None = None
    school: str | None = Field(default=None, min_length=1, max_length=200)
    jersey_number: str | None = Field(default=None, min_length=1, max_length=10)
    emergency_contact_name: str | None = Field(default=None, min_length=1, max_length=200)
    emergency_contact_phone: str | None = Field(default=None, min_length=1, max_length=32)
    emergency_contact_relation: str | None = Field(default=None, min_length=1, max_length=100)
    # Explicitly declared (rather than left to `extra="forbid"` alone) so a
    # client submitting one of these gets the field-specific 422 FR-033
    # requires, naming exactly what it tried to change.
    email: str | None = None
    role: str | None = None
    status: str | None = None
    created_at: datetime | None = None
    skill_level: str | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _reject_explicit_null_names(cls, value: object) -> object:
        # A `field_validator` only runs against a value the caller actually
        # submitted — an *omitted* key never reaches this method, since it
        # is satisfied by the field's default instead. So this fires only
        # for `{"first_name": null}`, which maps to a NOT NULL column and
        # must not reach `setattr` (constitution Principle VI).
        if value is None:
            raise ValueError("This field cannot be cleared.")
        return value


class PhotoUrls(BaseModel):
    model_config = ConfigDict(extra="forbid")

    photo_url: str
    thumbnail_url: str
