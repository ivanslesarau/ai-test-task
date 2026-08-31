"""Coach invitations — the invited person's side (US2, FR-011 – FR-019).
HTTP concerns only; every business rule lives in `CoachInvitationService`
(constitution Principle III). Mirrors `join_router.py`'s three-endpoint
shape and its per-origin throttle exactly (research.md R2-05): only an
unusable token counts against `ShareLinkService.check_lookup_throttle` —
every other refusal (address mismatch, wrong role, already assigned) is
not "guessing" and must not count against it.
"""

from fastapi import APIRouter, Request, Response

from app.core.config import Settings
from app.core.deps import (
    CoachInvitationServiceDep,
    CurrentUserDep,
    SettingsDep,
    ShareLinkServiceDep,
)
from app.core.errors import InvitationLinkInvalid
from app.schemas.coach import CoachInvitationPreview, CoachJoinResult, CoachRegistrationRequest

router = APIRouter(prefix="/coach-invitations", tags=["coach-invitations"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, *, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_idle_days * 24 * 60 * 60,
        path="/",
    )


@router.get("/{token}", response_model=CoachInvitationPreview)
async def preview_coach_invitation(
    token: str,
    request: Request,
    coach_invitation_service: CoachInvitationServiceDep,
    share_link_service: ShareLinkServiceDep,
) -> CoachInvitationPreview:
    """Public and unauthenticated (FR-011 – FR-013). Every unusable token
    — unknown, spent, revoked, superseded, expired, or an inviting
    trainer no longer Active — throws the single `InvitationLinkInvalid`,
    mapped to one 404 body regardless of which condition applied."""
    client_ip = _client_ip(request)
    await share_link_service.check_lookup_throttle(client_ip)
    try:
        preview = await coach_invitation_service.preview(token)
    except InvitationLinkInvalid:
        await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=False)
        raise
    await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=True)
    return preview


@router.post("/{token}/register", response_model=CoachJoinResult, status_code=201)
async def register_through_coach_invitation(
    token: str,
    body: CoachRegistrationRequest,
    request: Request,
    response: Response,
    coach_invitation_service: CoachInvitationServiceDep,
    share_link_service: ShareLinkServiceDep,
    settings: SettingsDep,
) -> CoachJoinResult:
    """FR-011, FR-013, FR-017, FR-018, FR-023. No `email`, `role`, or
    `trainer_id` in the request body — all three come from the
    invitation."""
    client_ip = _client_ip(request)
    await share_link_service.check_lookup_throttle(client_ip)
    try:
        result, raw_token = await coach_invitation_service.register(token, body)
    except InvitationLinkInvalid:
        # A resolvable token, then some other rejection (duplicate email,
        # a race), is not "guessing" and must not count against this
        # throttle — only an unusable token does (research.md R2-05).
        await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=False)
        raise
    await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=True)
    _set_session_cookie(response, token=raw_token, settings=settings)
    return result


@router.post("/{token}/accept", response_model=CoachJoinResult)
async def accept_coach_invitation(
    token: str,
    request: Request,
    user: CurrentUserDep,
    coach_invitation_service: CoachInvitationServiceDep,
    share_link_service: ShareLinkServiceDep,
) -> CoachJoinResult:
    """FR-012 – FR-019, FR-023. For a signed-in account.
    `CoachAddressMismatch`, `RoleCannotAccept`, and `CoachAlreadyAssigned`
    are refusals the caller provoked with a valid token, not guesses, so
    none of them touch the throttle — only `InvitationLinkInvalid` does,
    exactly as the other two endpoints above."""
    client_ip = _client_ip(request)
    await share_link_service.check_lookup_throttle(client_ip)
    try:
        result = await coach_invitation_service.accept(token, current_user=user)
    except InvitationLinkInvalid:
        await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=False)
        raise
    await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=True)
    return result
