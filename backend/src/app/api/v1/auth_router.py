from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response

from app.core.deps import (
    AuthServiceDep,
    BrandingServiceDep,
    CurrentUserDep,
    SettingsDep,
    TrainingContextServiceDep,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import (
    CurrentUser,
    InvitationCheckResponse,
    LoginRequest,
    SetupPasswordRequest,
)
from app.services.branding_service import BrandingService
from app.services.training_context_service import TrainingContextService

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, *, token: str, settings: SettingsDep) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_idle_days * 24 * 60 * 60,
        path="/",
    )


async def _to_current_user(
    user: User,
    training_context_service: TrainingContextService,
    branding_service: BrandingService,
) -> CurrentUser:
    photo_url = f"/media/photos/{user.profile.photo_key}" if user.profile.photo_key else None

    active_player_profile_id: str | None = None
    active_trainer_id: str | None = None
    context_count = 0
    if user.role_enum is UserRole.PLAYER_PARENT:
        # One call resolves-and-repairs the pair and lists it
        # (research.md R-24, R-36) — no second query for the count.
        contexts = await training_context_service.list_for_account(user)
        active_player_profile_id = contexts.active_player_profile_id
        active_trainer_id = contexts.active_trainer_id
        context_count = len(contexts.contexts)

    # Derived from the existence of a profile naming this account as its
    # child sign-in, never stored as a column (research.md R-38). Every
    # role but player_parent resolves False without a query, since no
    # player_profiles row can name a trainer, coach, or super admin.
    is_child_account = (
        user.role_enum is UserRole.PLAYER_PARENT
        and await training_context_service.is_child_account(user)
    )

    portal_branding = await branding_service.resolve_for_viewer(user)

    return CurrentUser(
        id=user.id,
        email=user.email,
        role=user.role,
        status=user.status,
        first_name=user.profile.first_name,
        last_name=user.profile.last_name,
        photo_url=photo_url,
        active_player_profile_id=active_player_profile_id,
        active_trainer_id=active_trainer_id,
        context_count=context_count,
        is_child_account=is_child_account,
        portal_branding=portal_branding,
    )


@router.post("/login", response_model=CurrentUser)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
    training_context_service: TrainingContextServiceDep,
    branding_service: BrandingServiceDep,
) -> CurrentUser:
    user, raw_token = await auth_service.sign_in(
        email=body.email, password=body.password, client_ip=_client_ip(request)
    )
    _set_session_cookie(response, token=raw_token, settings=settings)
    return await _to_current_user(user, training_context_service, branding_service)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
    session_token: Annotated[str | None, Cookie(alias="pp_session")] = None,
) -> None:
    if session_token is not None:
        await auth_service.sign_out(session_token)
    response.delete_cookie(key=settings.session_cookie_name, path="/")


@router.get("/session", response_model=CurrentUser)
async def get_session(
    user: CurrentUserDep,
    training_context_service: TrainingContextServiceDep,
    branding_service: BrandingServiceDep,
) -> CurrentUser:
    return await _to_current_user(user, training_context_service, branding_service)


@router.get("/setup-password/{token}", response_model=InvitationCheckResponse)
async def check_setup_invitation(
    token: str, auth_service: AuthServiceDep
) -> InvitationCheckResponse:
    email_hint, expires_at = await auth_service.check_invitation(token)
    return InvitationCheckResponse(email_hint=email_hint, expires_at=expires_at)


@router.post("/setup-password", status_code=204)
async def setup_password(body: SetupPasswordRequest, auth_service: AuthServiceDep) -> None:
    await auth_service.setup_password(body.token, body.password)
