from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import NotAuthenticated, PermissionDenied
from app.db.session import get_db_session
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.branding_service import BrandingService
from app.services.erasure_service import ErasureService
from app.services.join_service import JoinService
from app.services.ports.email_sender import EmailSender, get_email_sender
from app.services.ports.photo_storage import PhotoStorage, get_photo_storage
from app.services.profile_service import ProfileService
from app.services.share_link_service import ShareLinkService
from app.services.trainer_context_service import TrainerContextService
from app.services.trainer_service import TrainerService
from app.services.user_admin_service import UserAdminService

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_auth_service(db_session: DbSessionDep, settings: SettingsDep) -> AuthService:
    return AuthService(db_session, settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_email_sender_dep(settings: SettingsDep) -> EmailSender:
    return get_email_sender(settings)


EmailSenderDep = Annotated[EmailSender, Depends(get_email_sender_dep)]


def get_user_admin_service(
    db_session: DbSessionDep, settings: SettingsDep, email_sender: EmailSenderDep
) -> UserAdminService:
    return UserAdminService(db_session, settings, email_sender)


UserAdminServiceDep = Annotated[UserAdminService, Depends(get_user_admin_service)]


def get_photo_storage_dep(settings: SettingsDep) -> PhotoStorage:
    return get_photo_storage(settings.upload_dir)


PhotoStorageDep = Annotated[PhotoStorage, Depends(get_photo_storage_dep)]


def get_profile_service(
    db_session: DbSessionDep, settings: SettingsDep, photo_storage: PhotoStorageDep
) -> ProfileService:
    return ProfileService(db_session, settings, photo_storage)


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


def get_erasure_service(
    db_session: DbSessionDep, photo_storage: PhotoStorageDep, admin_service: UserAdminServiceDep
) -> ErasureService:
    return ErasureService(db_session, photo_storage, admin_service)


ErasureServiceDep = Annotated[ErasureService, Depends(get_erasure_service)]


async def get_current_user(
    request: Request,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
    session_token: Annotated[str | None, Cookie(alias="pp_session")] = None,
) -> User:
    if session_token is None:
        raise NotAuthenticated("Sign in to continue.")
    user = await auth_service.authenticate_session(session_token)
    request.state.current_user_id = user.id
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_user_optional(
    auth_service: AuthServiceDep,
    session_token: Annotated[str | None, Cookie(alias="pp_session")] = None,
) -> User | None:
    """For the one genuinely public endpoint that still tailors its
    response to a signed-in caller — the join-link preview (FR-073,
    FR-080 – FR-082). An invalid or absent cookie resolves to `None`
    rather than refusing the request; the route itself has `security: []`
    in the contract."""
    if session_token is None:
        return None
    try:
        return await auth_service.authenticate_session(session_token)
    except NotAuthenticated:
        return None


CurrentUserOptionalDep = Annotated[User | None, Depends(get_current_user_optional)]


def require_roles(
    *roles: UserRole,
) -> Callable[[User, AuthServiceDep], Coroutine[Any, Any, User]]:
    """Factory for a role-gate dependency. The role check needs only the
    session, so it runs and rejects an unauthorized caller before any
    route-specific work begins (research.md R-14).

    A refusal is recorded as a `permission_denied` audit entry (FR-020).
    """

    async def _dependency(user: CurrentUserDep, auth_service: AuthServiceDep) -> User:
        if user.role_enum not in roles:
            allowed = [r.value for r in roles]
            await auth_service.record_permission_denied(
                actor_user_id=user.id,
                detail=f"role={user.role} attempted an action requiring one of {allowed}",
            )
            raise PermissionDenied("Your role does not permit this action.")
        return user

    return _dependency


def get_share_link_service(db_session: DbSessionDep, settings: SettingsDep) -> ShareLinkService:
    return ShareLinkService(db_session, settings)


ShareLinkServiceDep = Annotated[ShareLinkService, Depends(get_share_link_service)]


def get_join_service(
    db_session: DbSessionDep, settings: SettingsDep, email_sender: EmailSenderDep
) -> JoinService:
    return JoinService(db_session, settings, email_sender)


JoinServiceDep = Annotated[JoinService, Depends(get_join_service)]


def get_trainer_service(db_session: DbSessionDep) -> TrainerService:
    return TrainerService(db_session)


TrainerServiceDep = Annotated[TrainerService, Depends(get_trainer_service)]


def get_trainer_context_service(db_session: DbSessionDep) -> TrainerContextService:
    return TrainerContextService(db_session)


TrainerContextServiceDep = Annotated[TrainerContextService, Depends(get_trainer_context_service)]


async def get_trainer_context(
    user: CurrentUserDep, trainer_context_service: TrainerContextServiceDep
) -> str | None:
    """The one place an endpoint learns "which trainer is this player
    currently looking at" (research.md R-25). No endpoint accepts a
    `trainer_id` parameter to select context — every context-scoped route
    Epics 02-08 add resolves it through this dependency instead, so an
    endpoint that forgets the check is merely wrong, not vulnerable. None
    for a non-player role, or a player with no Active association."""
    return await trainer_context_service.resolve_active_trainer_id(user)


TrainerContextDep = Annotated[str | None, Depends(get_trainer_context)]


def get_branding_service(
    db_session: DbSessionDep, photo_storage: PhotoStorageDep
) -> BrandingService:
    return BrandingService(db_session, photo_storage)


BrandingServiceDep = Annotated[BrandingService, Depends(get_branding_service)]
