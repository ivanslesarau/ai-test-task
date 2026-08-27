import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


class PortalBranding(BaseModel):
    """Matches contracts/openapi.yaml `PortalBranding`. Every value may be
    absent, and absent means the platform default — never an empty string
    (FR-104, constitution Principle VI)."""

    model_config = ConfigDict(extra="forbid")

    logo_url: str | None
    primary_color: str | None
    updated_at: datetime | None


class PortalBrandingUpdate(BaseModel):
    """An omitted key changes nothing; an explicit `null` clears the
    colour back to the platform default — read with
    `model_dump(exclude_unset=True)`, exactly as OwnProfileUpdate is."""

    model_config = ConfigDict(extra="forbid")

    primary_color: str | None = Field(default=None)

    @field_validator("primary_color")
    @classmethod
    def _valid_hex_when_present(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _HEX_COLOR_PATTERN.match(value):
            raise ValueError("Enter a colour as a 6-digit hex code, e.g. #3366CC.")
        return value.lower()


DEFAULT_PORTAL_BRANDING = PortalBranding(logo_url=None, primary_color=None, updated_at=None)


def build_portal_branding_out(trainer_org: object) -> PortalBranding:
    """Maps a TrainerOrganization row's three branding columns to the API
    shape. Absent trainer_org (a Super Admin, an unauthenticated visitor,
    a Coach not yet linked to an employer — research.md R-33) resolves to
    the platform default, never to an empty-string value (FR-104)."""
    from app.models.role_details import TrainerOrganization

    if trainer_org is None or not isinstance(trainer_org, TrainerOrganization):
        return DEFAULT_PORTAL_BRANDING
    return PortalBranding(
        logo_url=f"/media/branding/{trainer_org.logo_key}" if trainer_org.logo_key else None,
        primary_color=trainer_org.primary_color,
        updated_at=trainer_org.branding_updated_at,
    )
