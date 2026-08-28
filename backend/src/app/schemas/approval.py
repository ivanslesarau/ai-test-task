from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApprovalRequestKind, ApprovalRequestStatus


class ApprovalRequest(BaseModel):
    """One thing a child asked for and a parent must decide (FR-141),
    matching contracts/openapi.yaml `ApprovalRequest`. `player_display_name`
    and `trainer_display_name` are resolved by the service, never inferred
    client-side (frontend-contracts.md §20)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    player_profile_id: str
    player_display_name: str
    kind: ApprovalRequestKind
    status: ApprovalRequestStatus
    trainer_id: str | None = None
    trainer_display_name: str | None = None
    amount_minor: int | None = None
    currency: str | None = None
    requested_at: datetime
    expires_at: datetime
    parent_note: str | None = None
    child_note: str | None = None
    resolved_at: datetime | None = None
    # Who resolved it — derived by the service from `resolved_by_user_id`
    # against the parent account and the child's own sign-in, never the
    # raw user id (R-43: null for an expiry, which nobody performed).
    resolved_by: str | None = None


class ApprovalRequestPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ApprovalRequest]
    page: int
    page_size: int
    total: int


class ApprovalDecisionRequest(BaseModel):
    """The body `approve`, `deny`, and (for symmetry with the withdraw
    route's lack of one) nothing else carries (FR-150). `note` is optional
    — constitution Principle VI: `str | None` with `min_length=1` so an
    opened-but-empty note box must send `null`, never `''`."""

    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, min_length=1, max_length=1000)


class ApprovalInfoRequest(BaseModel):
    """The body `request-info` and `respond` carry. `note` is REQUIRED here
    — asking for more information without saying what is wanted, or
    replying without saying anything, is not a message (FR-150, FR-153)."""

    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=1, max_length=1000)
