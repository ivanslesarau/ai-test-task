from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from app.core.deps import (
    BrandingServiceDep,
    CurrentUserDep,
    ProfileServiceDep,
    ShareLinkServiceDep,
    TrainerContextServiceDep,
    require_roles,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.branding import PortalBranding, PortalBrandingUpdate
from app.schemas.profile import OwnProfile, OwnProfileUpdate, PhotoUrls
from app.schemas.share_link import ShareLinkOut
from app.schemas.trainer_context import TrainerContextList, TrainerContextRequest

router = APIRouter(prefix="/me", tags=["me"])

TrainerOnlyDep = Annotated[User, Depends(require_roles(UserRole.TRAINER))]
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


# --- Extension (2026-08-26): multi-trainer context --------------------------


@router.get("/trainers", response_model=TrainerContextList)
async def list_own_trainers(
    user: PlayerParentOnlyDep, trainer_context_service: TrainerContextServiceDep
) -> TrainerContextList:
    return await trainer_context_service.list_for_player(user)


@router.put("/trainer-context", response_model=TrainerContextList)
async def switch_trainer_context(
    body: TrainerContextRequest,
    user: PlayerParentOnlyDep,
    trainer_context_service: TrainerContextServiceDep,
) -> TrainerContextList:
    """The only endpoint that changes context. No other endpoint accepts
    a trainer identifier, because context is a data-isolation boundary
    rather than a view preference (research.md R-25)."""
    return await trainer_context_service.switch(user, body.trainer_id)


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
