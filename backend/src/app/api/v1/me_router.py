from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from app.core.deps import (
    AvailabilityServiceDep,
    BrandingServiceDep,
    CurrentUserDep,
    ProfileServiceDep,
    ShareLinkServiceDep,
    TrainingContextServiceDep,
    require_roles,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.availability import AvailabilityWeekOut, AvailabilityWeekUpdate
from app.schemas.branding import PortalBranding, PortalBrandingUpdate
from app.schemas.profile import OwnProfile, OwnProfileUpdate, PhotoUrls
from app.schemas.share_link import ShareLinkOut
from app.schemas.training_context import TrainingContextList, TrainingContextRequest

router = APIRouter(prefix="/me", tags=["me"])

TrainerOnlyDep = Annotated[User, Depends(require_roles(UserRole.TRAINER))]
CoachOnlyDep = Annotated[User, Depends(require_roles(UserRole.COACH))]
PlayerParentOnlyDep = Annotated[User, Depends(require_roles(UserRole.PLAYER_PARENT))]


@router.get("/profile", response_model=OwnProfile)
async def get_own_profile(user: CurrentUserDep, profile_service: ProfileServiceDep) -> OwnProfile:
    return await profile_service.get_own_profile(user)


@router.patch("/profile", response_model=OwnProfile)
async def update_own_profile(
    body: OwnProfileUpdate, user: CurrentUserDep, profile_service: ProfileServiceDep
) -> OwnProfile:
    updates = body.model_dump(exclude_unset=True)
    return await profile_service.update_own_profile(user, updates)


@router.put("/profile/photo", response_model=PhotoUrls)
async def upload_own_photo(
    file: UploadFile, user: CurrentUserDep, profile_service: ProfileServiceDep
) -> PhotoUrls:
    data = await file.read()
    return await profile_service.upload_own_photo(user, data)


@router.delete("/profile/photo", status_code=204)
async def delete_own_photo(user: CurrentUserDep, profile_service: ProfileServiceDep) -> None:
    await profile_service.delete_own_photo(user)


# --- Extension (2026-08-26): ShareLink onboarding ---------------------------


@router.get("/share-link", response_model=ShareLinkOut)
async def get_own_share_link(
    user: TrainerOnlyDep, share_link_service: ShareLinkServiceDep
) -> ShareLinkOut:
    return await share_link_service.get_current_for_trainer(user)


@router.post("/share-link/regenerate", response_model=ShareLinkOut, status_code=201)
async def regenerate_own_share_link(
    user: TrainerOnlyDep, share_link_service: ShareLinkServiceDep
) -> ShareLinkOut:
    return await share_link_service.regenerate(user)


# --- Extension (2026-08-27): family accounts — profile-and-trainer context --


@router.get("/contexts", response_model=TrainingContextList)
async def list_own_contexts(
    user: PlayerParentOnlyDep, training_context_service: TrainingContextServiceDep
) -> TrainingContextList:
    """Replaces `GET /me/trainers` (research.md R-49) — every entry now
    names both the profile and the trainer (FR-117, FR-118)."""
    return await training_context_service.list_for_account(user)


@router.put("/context", response_model=TrainingContextList)
async def switch_training_context(
    body: TrainingContextRequest,
    user: PlayerParentOnlyDep,
    training_context_service: TrainingContextServiceDep,
) -> TrainingContextList:
    """Replaces `PUT /me/trainer-context` (research.md R-49) — the only
    endpoint that changes context. Both halves of the pair are named in
    the body, never a path or query parameter, because context is a
    data-isolation boundary rather than a view preference (research.md
    R-25, R-48)."""
    return await training_context_service.switch(
        user, player_profile_id=body.player_profile_id, trainer_id=body.trainer_id
    )


# --- Extension (2026-08-26): trainer portal branding -------------------------


@router.get("/branding", response_model=PortalBranding)
async def get_own_branding(
    user: TrainerOnlyDep, branding_service: BrandingServiceDep
) -> PortalBranding:
    return await branding_service.get_own(user)


@router.patch("/branding", response_model=PortalBranding)
async def update_own_branding(
    body: PortalBrandingUpdate, user: TrainerOnlyDep, branding_service: BrandingServiceDep
) -> PortalBranding:
    updates = body.model_dump(exclude_unset=True)
    if "primary_color" not in updates:
        return await branding_service.get_own(user)
    return await branding_service.update_color(user, primary_color=updates["primary_color"])


@router.put("/branding/logo", response_model=PortalBranding)
async def upload_own_logo(
    file: UploadFile, user: TrainerOnlyDep, branding_service: BrandingServiceDep
) -> PortalBranding:
    data = await file.read()
    return await branding_service.upload_logo(user, data)


@router.delete("/branding/logo", status_code=204)
async def delete_own_logo(user: TrainerOnlyDep, branding_service: BrandingServiceDep) -> None:
    await branding_service.delete_logo(user)


@router.post("/branding/reset", response_model=PortalBranding)
async def reset_own_branding(
    user: TrainerOnlyDep, branding_service: BrandingServiceDep
) -> PortalBranding:
    return await branding_service.reset(user)


# --- Extension (2026-08-28): a coach's own weekly availability (US3) --------


@router.get("/availability", response_model=AvailabilityWeekOut)
async def get_own_availability(
    user: CoachOnlyDep, availability_service: AvailabilityServiceDep
) -> AvailabilityWeekOut:
    """Never-stated returns `slots: [], updated_at: null` (FR-035) — there
    is nothing to distinguish "no rows yet" from any other read."""
    return await availability_service.get_week(coach_user_id=user.id)


@router.put("/availability", response_model=AvailabilityWeekOut)
async def replace_own_availability(
    body: AvailabilityWeekUpdate, user: CoachOnlyDep, availability_service: AvailabilityServiceDep
) -> AvailabilityWeekOut:
    """Whole-week replace, validated before anything is written (FR-027,
    FR-029) — a refused save leaves the previous week exactly as it was."""
    return await availability_service.replace_week(body, coach_user_id=user.id)


@router.delete("/availability", status_code=204)
async def clear_own_availability(
    user: CoachOnlyDep, availability_service: AvailabilityServiceDep
) -> None:
    """Deliberately distinct from never-stated: `updated_at` is stamped
    (FR-030, FR-032, FR-035)."""
    await availability_service.clear_week(coach_user_id=user.id)
