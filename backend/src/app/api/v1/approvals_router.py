from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import ApprovalServiceDep, RequireParentDep, require_roles
from app.models.enums import ApprovalRequestStatus, UserRole
from app.models.user import User
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalInfoRequest,
    ApprovalRequest,
    ApprovalRequestPage,
)

router = APIRouter(tags=["approvals"])

# A signed-in child is an ordinary `player_parent` account (research.md
# R-38) — the `/me/requests` routes below deliberately use this role-only
# gate rather than `RequireParentDep`, since the child raising the
# request must be able to read and act on it. Ownership of a specific
# request is enforced inside `ApprovalService`, not by this role gate.
PlayerParentOnlyDep = Annotated[User, Depends(require_roles(UserRole.PLAYER_PARENT))]


# --- the parent's decision queue (FR-149, FR-159) ---------------------------


@router.get("/me/approvals", response_model=ApprovalRequestPage)
async def list_own_approvals(
    user: RequireParentDep,
    approval_service: ApprovalServiceDep,
    status: ApprovalRequestStatus | None = None,
    player_profile_id: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ApprovalRequestPage:
    """Parent only. Defaults to the live statuses — a decision queue, not
    a history (FR-149)."""
    return await approval_service.list_for_parent(
        user.id,
        status=status.value if status is not None else None,
        player_profile_id=player_profile_id,
        page=page,
        page_size=page_size,
    )


@router.get("/me/approvals/{request_id}", response_model=ApprovalRequest)
async def get_own_approval(
    request_id: str, user: RequireParentDep, approval_service: ApprovalServiceDep
) -> ApprovalRequest:
    """404, not 403, for a request belonging to another account's child
    (research.md R-48)."""
    return await approval_service.get_own_approval(user.id, request_id)


@router.post("/me/approvals/{request_id}/approve", response_model=ApprovalRequest)
async def approve_own_approval(
    request_id: str,
    user: RequireParentDep,
    approval_service: ApprovalServiceDep,
    body: ApprovalDecisionRequest | None = None,
) -> ApprovalRequest:
    """The action is carried out in the same transaction as the status
    change (FR-151), exactly once (FR-144)."""
    note = body.note if body is not None else None
    return await approval_service.approve(user.id, request_id, note=note)


@router.post("/me/approvals/{request_id}/deny", response_model=ApprovalRequest)
async def deny_own_approval(
    request_id: str,
    user: RequireParentDep,
    approval_service: ApprovalServiceDep,
    body: ApprovalDecisionRequest | None = None,
) -> ApprovalRequest:
    note = body.note if body is not None else None
    return await approval_service.deny(user.id, request_id, note=note)


@router.post("/me/approvals/{request_id}/request-info", response_model=ApprovalRequest)
async def request_info_on_own_approval(
    request_id: str,
    body: ApprovalInfoRequest,
    user: RequireParentDep,
    approval_service: ApprovalServiceDep,
) -> ApprovalRequest:
    """Moves to `info_requested`, a live status — `expires_at` is never
    touched (FR-155, research.md R-43)."""
    return await approval_service.request_info(user.id, request_id, note=body.note)


# --- the child's own view of what they raised (FR-131, FR-153) -------------


@router.get("/me/requests", response_model=ApprovalRequestPage)
async def list_own_raised_requests(
    user: PlayerParentOnlyDep,
    approval_service: ApprovalServiceDep,
    status: ApprovalRequestStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ApprovalRequestPage:
    return await approval_service.list_raised_by(
        user.id, status=status.value if status is not None else None, page=page, page_size=page_size
    )


@router.post("/me/requests/{request_id}/withdraw", response_model=ApprovalRequest)
async def withdraw_own_request(
    request_id: str, user: PlayerParentOnlyDep, approval_service: ApprovalServiceDep
) -> ApprovalRequest:
    """Only the child the request concerns, and only while it is still
    live (FR-154, FR-156)."""
    return await approval_service.withdraw(user.id, request_id)


@router.post("/me/requests/{request_id}/respond", response_model=ApprovalRequest)
async def respond_to_own_request(
    request_id: str,
    body: ApprovalInfoRequest,
    user: PlayerParentOnlyDep,
    approval_service: ApprovalServiceDep,
) -> ApprovalRequest:
    """Only from `info_requested`, back to `pending_parent_approval`,
    without restarting the 48-hour deadline (FR-143, FR-155)."""
    return await approval_service.respond(user.id, request_id, note=body.note)
