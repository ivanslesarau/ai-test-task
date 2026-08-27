from fastapi import APIRouter, Request, Response

from app.core.config import Settings
from app.core.deps import (
    CurrentUserDep,
    CurrentUserOptionalDep,
    JoinServiceDep,
    SettingsDep,
    ShareLinkServiceDep,
)
from app.core.errors import InvitationLinkInvalid
from app.schemas.join import JoinLinkPreview, JoinRegistrationRequest, JoinResult

router = APIRouter(prefix="/join", tags=["join"])


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


@router.get("/{code}", response_model=JoinLinkPreview)
async def preview_join_link(
    code: str,
    request: Request,
    join_service: JoinServiceDep,
    share_link_service: ShareLinkServiceDep,
    current_user: CurrentUserOptionalDep,
) -> JoinLinkPreview:
    """Public and unauthenticated (FR-073). Every refusal — unknown,
    revoked, expired, exhausted, owner not Active — is thrown by
    JoinService.preview as the single InvitationLinkInvalid, mapped to one
    404 body regardless of which condition applied (FR-070)."""
    client_ip = _client_ip(request)
    await share_link_service.check_lookup_throttle(client_ip)
    try:
        preview = await join_service.preview(code, current_user=current_user)
    except InvitationLinkInvalid:
        # Only "the code itself is not usable" counts against the
        # guessing throttle (FR-071) — a preview never raises anything
        # else, so this is the only branch here.
        await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=False)
        raise
    await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=True)
    return preview


@router.post("/{code}/register", response_model=JoinResult, status_code=201)
async def register_through_join_link(
    code: str,
    body: JoinRegistrationRequest,
    request: Request,
    response: Response,
    join_service: JoinServiceDep,
    share_link_service: ShareLinkServiceDep,
    settings: SettingsDep,
) -> JoinResult:
    client_ip = _client_ip(request)
    await share_link_service.check_lookup_throttle(client_ip)
    try:
        result, raw_token = await join_service.register(code, body, client_ip=client_ip)
    except InvitationLinkInvalid:
        # A resolvable code, then some other rejection (duplicate email,
        # a race), is not "guessing" and must not count against this
        # throttle — only an unusable code does (FR-071).
        await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=False)
        raise
    await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=True)
    _set_session_cookie(response, token=raw_token, settings=settings)
    return result


@router.post("/{code}/accept", response_model=JoinResult)
async def accept_join_link(
    code: str,
    request: Request,
    user: CurrentUserDep,
    join_service: JoinServiceDep,
    share_link_service: ShareLinkServiceDep,
) -> JoinResult:
    client_ip = _client_ip(request)
    await share_link_service.check_lookup_throttle(client_ip)
    try:
        result = await join_service.accept(code, current_user=user)
    except InvitationLinkInvalid:
        await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=False)
        raise
    await share_link_service.record_lookup_attempt(client_ip=client_ip, successful=True)
    return result
