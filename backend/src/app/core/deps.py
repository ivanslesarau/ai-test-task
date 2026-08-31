from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import NotAuthenticated, NotFound, PermissionDenied
from app.core.principal import ImpersonationContext, Principal
from app.db.session import get_db_session
from app.models.auth import Session as SessionModel
from app.models.enums import UserRole
from app.models.user import User
from app.services.approval_service import ApprovalService
from app.services.auth_service import AuthService
from app.services.availability_service import AvailabilityService
from app.services.branding_service import BrandingService
from app.services.child_signin_service import ChildSigninService
from app.services.coach_invitation_service import CoachInvitationService
from app.services.coach_service import CoachService
from app.services.erasure_service import ErasureService
from app.services.family_service import FamilyService
from app.services.impersonation_service import ImpersonationService
from app.services.join_service import JoinService
from app.services.ports.email_sender import EmailSender, get_email_sender
from app.services.ports.photo_storage import PhotoStorage, get_photo_storage
from app.services.profile_service import ProfileService
from app.services.share_link_service import ShareLinkService
from app.services.trainer_service import TrainerService
from app.services.training_context_service import TrainingContextService
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
    db_session: DbSessionDep,
    photo_storage: PhotoStorageDep,
    admin_service: UserAdminServiceDep,
    settings: SettingsDep,
) -> ErasureService:
    return ErasureService(db_session, photo_storage, admin_service, settings)


ErasureServiceDep = Annotated[ErasureService, Depends(get_erasure_service)]


def get_impersonation_service(
    db_session: DbSessionDep, settings: SettingsDep
) -> ImpersonationService:
    return ImpersonationService(db_session, settings)


ImpersonationServiceDep = Annotated[ImpersonationService, Depends(get_impersonation_service)]


async def get_principal(
    request: Request,
    db_session: DbSessionDep,
    auth_service: AuthServiceDep,
    impersonation_service: ImpersonationServiceDep,
    session_token: Annotated[str | None, Cookie(alias="pp_session")] = None,
) -> Principal:
    """The one substitution point every existing endpoint's caller
    resolves through (research.md R2-14). `authenticate_session_record`
    keeps `AuthService`'s own session rules exactly as feature 001 wrote
    them; `ImpersonationService.resolve_for_session` is where an open
    impersonation is read, and — on the first request past its deadline,
    its target's erasure, or its target leaving Active status it started
    in — ended (research.md R2-19).
    """
    if session_token is None:
        raise NotAuthenticated("Sign in to continue.")
    real_user, session_record = await auth_service.authenticate_session_record(session_token)
    principal = await impersonation_service.resolve_for_session(real_user, session_record)

    if principal.impersonation is not None:
        # research.md R2-16: the single request-scoped carrier
        # `AuditRepository.add` reads into `audit_entries
        # .impersonator_user_id`. Left unset for an ordinary request, so
        # every existing audit call site keeps writing `NULL` exactly as
        # it did before this feature.
        db_session.info["impersonator_user_id"] = principal.real_user.id

    request.state.current_user_id = principal.effective_user.id
    # A side channel for `get_current_session_record` below — the only two
    # routes that need the `sessions` row itself, not just the identities
    # resolved from it (starting and ending an impersonation), reuse this
    # request's already-resolved record instead of a second session
    # lookup.
    request.state.session_record = session_record
    return principal


PrincipalDep = Annotated[Principal, Depends(get_principal)]


async def get_current_session_record(request: Request, principal: PrincipalDep) -> SessionModel:
    """The `sessions` row backing this request's cookie (data-model.md
    §106) — needed only by `POST /admin/impersonations` and `DELETE
    /admin/impersonations/current`, which set or clear
    `sessions.impersonation_id` on the exact row `get_principal` already
    authenticated this request against."""
    _ = principal  # ensures get_principal has run and stashed the record
    record: SessionModel = request.state.session_record
    return record


CurrentSessionRecordDep = Annotated[SessionModel, Depends(get_current_session_record)]


async def get_current_user(principal: PrincipalDep) -> User:
    """A one-line wrapper over `get_principal` (research.md R2-14): every
    pre-existing dependency and router signature that depends on
    `CurrentUserDep` is unchanged by this feature, and each sees exactly
    the impersonated person's capabilities while an impersonation is live
    — the entire mechanism FR-043 relies on."""
    return principal.effective_user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_impersonation_context(principal: PrincipalDep) -> ImpersonationContext | None:
    return principal.impersonation


ImpersonationContextDep = Annotated[ImpersonationContext | None, Depends(get_impersonation_context)]


async def get_real_admin_with_open_impersonation(principal: PrincipalDep) -> Principal:
    """research.md R2-15: the exit route's own dependency. It authorizes
    on `principal.real_user`, never `require_roles(SUPER_ADMIN)` —
    while impersonating anyone but another Super Admin, the *effective*
    user fails that role gate, which would lock the admin inside the
    impersonation until the one-hour ceiling instead of letting them
    leave. `real_user` is already guaranteed to be an Active account by
    `authenticate_session_record`, and can only be riding an open
    impersonation if it was a Super Admin at the moment `POST
    /admin/impersonations` — itself gated by `require_roles(SUPER_ADMIN)`
    — created it. The one check this dependency adds is therefore exactly
    "does this session hold an open impersonation"; a caller with none
    reaches the route as a 404, matching the contract, including the case
    where it has *just* ended on the deadline."""
    if principal.impersonation is None:
        raise NotFound("No impersonation is in progress.")
    return principal


RealAdminWithOpenImpersonationDep = Annotated[
    Principal, Depends(get_real_admin_with_open_impersonation)
]


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


def get_training_context_service(db_session: DbSessionDep) -> TrainingContextService:
    return TrainingContextService(db_session)


TrainingContextServiceDep = Annotated[TrainingContextService, Depends(get_training_context_service)]


_require_player_parent_role = require_roles(UserRole.PLAYER_PARENT)


async def require_parent(
    user: Annotated[User, Depends(_require_player_parent_role)],
    auth_service: AuthServiceDep,
    training_context_service: TrainingContextServiceDep,
) -> User:
    """FR-132, FR-133: refuses a caller whose account is a signed-in
    child, on top of the existing player_parent role gate every family
    endpoint already carries. FR-132's child is an ordinary `player_parent`
    account (research.md R-38), so `require_roles` alone cannot keep them
    out; `TrainingContextService.is_child_account` is the one place
    "is this caller a child sign-in" is derived (research.md R-38), reused
    here rather than re-queried. Every action FR-132 forbids is refused
    **on the request** — this dependency, not a hidden control — exactly
    as `require_roles` records a `permission_denied` audit entry for its
    own refusal (FR-020)."""
    if await training_context_service.is_child_account(user):
        await auth_service.record_permission_denied(
            actor_user_id=user.id,
            detail="child sign-in attempted an action reserved for the owning parent",
        )
        raise PermissionDenied("Only the account holder can do this.")
    return user


RequireParentDep = Annotated[User, Depends(require_parent)]


def get_child_signin_service(
    db_session: DbSessionDep, settings: SettingsDep, email_sender: EmailSenderDep
) -> ChildSigninService:
    return ChildSigninService(db_session, settings, email_sender)


ChildSigninServiceDep = Annotated[ChildSigninService, Depends(get_child_signin_service)]


@dataclass(frozen=True)
class ResolvedTrainingContext:
    """The validated `(player_profile_id, trainer_user_id)` pair
    (data-model.md §27, research.md R-36, R-48). Both fields are `None`
    together — a caller with no reachable context — or both set; nothing
    in this codebase ever writes the mixed state, and `TrainingContextService`
    treats one as the other on read."""

    player_profile_id: str | None
    trainer_id: str | None


async def get_training_context(
    user: CurrentUserDep, training_context_service: TrainingContextServiceDep
) -> ResolvedTrainingContext:
    """The one place an endpoint learns "which player profile and which
    trainer is this account currently looking at" (research.md R-25,
    R-48). Renamed from `get_trainer_context`: the boundary is now a pair,
    because a sibling on the same account is a different context even
    with the same trainer (FR-117). No endpoint accepts a `player_profile_id`
    or `trainer_id` parameter to select context — every context-scoped
    route Epics 02-08 add resolves it through this dependency instead, so
    an endpoint that forgets the check is merely wrong, not vulnerable.
    Both fields are `None` for a non-player role, a signed-in child's
    account before Phase C exists, or a player with no Active
    association."""
    player_profile_id, trainer_id = await training_context_service.resolve_active_context(user)
    return ResolvedTrainingContext(player_profile_id=player_profile_id, trainer_id=trainer_id)


TrainingContextDep = Annotated[ResolvedTrainingContext, Depends(get_training_context)]


def get_branding_service(
    db_session: DbSessionDep, photo_storage: PhotoStorageDep
) -> BrandingService:
    return BrandingService(db_session, photo_storage)


BrandingServiceDep = Annotated[BrandingService, Depends(get_branding_service)]


def get_family_service(
    db_session: DbSessionDep,
    settings: SettingsDep,
    photo_storage: PhotoStorageDep,
    share_link_service: ShareLinkServiceDep,
) -> FamilyService:
    return FamilyService(db_session, settings, photo_storage, share_link_service)


FamilyServiceDep = Annotated[FamilyService, Depends(get_family_service)]


def get_approval_service(
    db_session: DbSessionDep, settings: SettingsDep, email_sender: EmailSenderDep
) -> ApprovalService:
    return ApprovalService(db_session, settings, email_sender)


ApprovalServiceDep = Annotated[ApprovalService, Depends(get_approval_service)]


# --- Extension (2026-08-28): availability (US3, US4) ------------------------


def get_availability_service(db_session: DbSessionDep) -> AvailabilityService:
    return AvailabilityService(db_session)


AvailabilityServiceDep = Annotated[AvailabilityService, Depends(get_availability_service)]


# --- Extension (2026-08-28): coach invitations (US1, US2) -------------------


def get_coach_invitation_service(
    db_session: DbSessionDep, settings: SettingsDep, email_sender: EmailSenderDep
) -> CoachInvitationService:
    return CoachInvitationService(db_session, settings, email_sender)


CoachInvitationServiceDep = Annotated[CoachInvitationService, Depends(get_coach_invitation_service)]


def get_coach_service(db_session: DbSessionDep) -> CoachService:
    return CoachService(db_session)


CoachServiceDep = Annotated[CoachService, Depends(get_coach_service)]
