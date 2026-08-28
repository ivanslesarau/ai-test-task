from pydantic import BaseModel, ConfigDict, EmailStr, Field


class GrantChildSignInRequest(BaseModel):
    """The email that becomes this child's login (FR-129). Subject to the
    platform-wide uniqueness rule across every status, so the parent's own
    address is refused rather than shared (FR-004) — enforced the same way
    every other account-creation path enforces it, not reimplemented here."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)


class ChildSignIn(BaseModel):
    """The result of granting a child a sign-in (contract's `ChildSignIn`)."""

    model_config = ConfigDict(extra="forbid")

    player_profile_id: str
    email: str
    invitation_sent: bool
    """False when the setup invitation could not be delivered. A failed
    delivery is never reported as success; re-grant to try again (FR-064)."""
