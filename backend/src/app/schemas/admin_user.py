import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import UserRole
from app.schemas.role_detail import RoleDetailOut

# FR-050's counterpart: creating an account whose email collides with the
# erasure placeholder pattern is rejected (data-model.md §10).
_ERASURE_PLACEHOLDER_PATTERN = re.compile(r"^deleted_[0-9a-f-]{36}@example\.com$", re.IGNORECASE)


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Typed as the enum, not `str`: an invalid role value must be a 422
    # from Pydantic's own validation (FR-022, one offending field named),
    # not a bare ValueError surfacing as a 500 from `UserRole(body.role)`
    # deep in the router.
    role: UserRole
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=32)
    business_name: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def _business_name_matches_role(self) -> "CreateUserRequest":
        if self.role == "trainer" and not self.business_name:
            raise ValueError("business_name is required when role is trainer")
        if self.role != "trainer" and self.business_name:
            raise ValueError("business_name is only accepted when role is trainer")
        return self

    @field_validator("email")
    @classmethod
    def _email_not_a_reserved_placeholder(cls, value: str) -> str:
        # A field_validator, not a model_validator, so the resulting 422
        # attributes to the "email" field specifically (FR-022) rather
        # than to the request body as a whole.
        if _ERASURE_PLACEHOLDER_PATTERN.match(value):
            raise ValueError("This email address format is reserved and cannot be used.")
        return value


class UserSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    status: str
    created_at: datetime
    thumbnail_url: str | None
    has_password: bool


class UserDetail(UserSummary):
    version: int
    phone: str | None
    photo_url: str | None
    role_detail: RoleDetailOut
    last_login_at: datetime | None
    available_actions: list[str]


class CreatedUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: UserDetail
    invitation_sent: bool
    invitation_expires_at: datetime


class StatusChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int


class EraseUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    reason: str = Field(min_length=1, max_length=1000)


class AuditActorOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str


class AuditEntryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    action: str
    actor: AuditActorOut | None
    reason: str | None
    detail: str | None
    occurred_at: datetime


class ErasureRecordOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    original_email: str
    original_first_name: str
    original_last_name: str
    erased_by: AuditActorOut
    reason: str
    erased_at: datetime
