from fastapi import APIRouter, UploadFile

from app.core.deps import CurrentUserDep, ProfileServiceDep
from app.schemas.profile import OwnProfile, OwnProfileUpdate, PhotoUrls

router = APIRouter(prefix="/me", tags=["me"])


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
