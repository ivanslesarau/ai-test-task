from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from app.core.deps import (
    AvailabilityServiceDep,
    ChildSigninServiceDep,
    FamilyServiceDep,
    RequireParentDep,
    require_roles,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.availability import AvailabilityWeekOut, AvailabilityWeekUpdate
from app.schemas.child_signin import ChildSignIn, GrantChildSignInRequest
from app.schemas.player_profile import (
    AddPlayerTrainerRequest,
    CreateChildProfileRequest,
    PlayerProfile,
    PlayerProfileList,
    PlayerProfileUpdate,
)
from app.schemas.profile import PhotoUrls

router = APIRouter(prefix="/me/players", tags=["family"])

# `require_roles` alone is not enough to keep a signed-in child out —
# FR-132's child is an ordinary `player_parent` account (research.md
# R-38). The read-only routes below (list, get, upload own photo) are
# among the few things FR-131 permits a child, so they keep this
# role-only gate; every route that changes anything belonging to the
# parent or to a sibling, or changes a setting the parent owns (FR-132),
# uses `RequireParentDep` instead (T373), which layers the child refusal
# on top of this same role check — EXCEPT `PATCH /{profile_id}`, which
# keeps this role-only gate deliberately: FamilyService.update_profile's
# own child check produces the contract's more specific
# `parent_only_field` (FR-147), which RequireParentDep's generic
# `forbidden` would shadow before the service ever ran.
PlayerParentOnlyDep = Annotated[User, Depends(require_roles(UserRole.PLAYER_PARENT))]


@router.get("", response_model=PlayerProfileList)
async def list_own_players(
    user: PlayerParentOnlyDep, family_service: FamilyServiceDep
) -> PlayerProfileList:
    """A signed-in child receives only their own profile (FR-132) — the
    scoping happens inside the service, not here."""
    return await family_service.list_profiles(user)


@router.post("", response_model=PlayerProfile, status_code=201)
async def create_own_child_player(
    body: CreateChildProfileRequest, user: RequireParentDep, family_service: FamilyServiceDep
) -> PlayerProfile:
    """Parent only — a signed-in child cannot own a profile (FR-132)."""
    return await family_service.create_child(user, body)


@router.get("/{profile_id}", response_model=PlayerProfile)
async def get_own_player(
    profile_id: str, user: PlayerParentOnlyDep, family_service: FamilyServiceDep
) -> PlayerProfile:
    """404, not 403, for a profile the caller may not reach — another
    account's, or a sibling's when the caller is a child (FR-112,
    FR-132, research.md R-48)."""
    return await family_service.get_profile(user, profile_id)


@router.patch("/{profile_id}", response_model=PlayerProfile)
async def update_own_player(
    profile_id: str,
    body: PlayerProfileUpdate,
    user: PlayerParentOnlyDep,
    family_service: FamilyServiceDep,
) -> PlayerProfile:
    """Deliberately `PlayerParentOnlyDep`, not `RequireParentDep`: a
    signed-in child submitting a non-empty body here is refused by
    `FamilyService.update_profile` with the more specific
    `parent_only_field` (FR-132, FR-147) — the exact code the contract
    and quickstart 11.6 require — which `RequireParentDep`'s generic
    `forbidden` would shadow before the service ever ran."""
    updates = body.model_dump(exclude_unset=True)
    return await family_service.update_profile(user, profile_id, updates)


@router.delete("/{profile_id}", status_code=204)
async def delete_own_player(
    profile_id: str, user: RequireParentDep, family_service: FamilyServiceDep
) -> None:
    """A soft removal (FR-111); every historical record survives."""
    await family_service.remove_profile(user, profile_id)


@router.put("/{profile_id}/photo", response_model=PhotoUrls)
async def upload_own_player_photo(
    profile_id: str,
    file: UploadFile,
    user: PlayerParentOnlyDep,
    family_service: FamilyServiceDep,
) -> PhotoUrls:
    """Accepted for the owning parent on any profile, and for a signed-in
    child on their own profile — one of the few things FR-131 permits
    them. `PlayerParentOnlyDep` still applies here because a signed-in
    child *is* a `player_parent` account (research.md R-38); which
    profile this caller may reach is what `FamilyService` checks."""
    data = await file.read()
    return await family_service.upload_photo(user, profile_id, data)


# --- Extension: trainer management on a player profile (US10) --------------


@router.post("/{profile_id}/trainers", response_model=PlayerProfile)
async def add_own_player_trainer(
    profile_id: str,
    body: AddPlayerTrainerRequest,
    user: RequireParentDep,
    family_service: FamilyServiceDep,
) -> PlayerProfile:
    """Parent only — a child changes no association, including their own
    (FR-128, FR-132)."""
    return await family_service.add_trainer(user, profile_id, body)


@router.delete("/{profile_id}/trainers/{association_id}", status_code=204)
async def remove_own_player_trainer(
    profile_id: str,
    association_id: str,
    user: RequireParentDep,
    family_service: FamilyServiceDep,
) -> None:
    """Addressed by the association's own identifier, never the
    trainer's, which keeps `trainer_id` out of path parameters where CI
    forbids it (research.md R-25, R-48)."""
    await family_service.remove_trainer(user, profile_id, association_id)


# --- Extension: a child's own sign-in (US11) --------------------------------


@router.put("/{profile_id}/sign-in", response_model=ChildSignIn, status_code=201)
async def grant_own_child_signin(
    profile_id: str,
    body: GrantChildSignInRequest,
    user: RequireParentDep,
    child_signin_service: ChildSigninServiceDep,
) -> ChildSignIn:
    """Parent only, and only for a `child` profile — a `self` profile's
    sign-in is the account itself (research.md R-37, FR-129)."""
    return await child_signin_service.grant(user, profile_id, body)


@router.delete("/{profile_id}/sign-in", status_code=204)
async def revoke_own_child_signin(
    profile_id: str,
    user: RequireParentDep,
    child_signin_service: ChildSigninServiceDep,
) -> None:
    """Every session that account holds stops working immediately
    (FR-134); the profile, its associations, and its history are
    untouched."""
    await child_signin_service.revoke(user, profile_id)


# --- Extension (2026-08-28): a player profile's weekly availability (US4) --


@router.get("/{profile_id}/availability", response_model=AvailabilityWeekOut)
async def get_player_availability(
    profile_id: str,
    user: PlayerParentOnlyDep,
    family_service: FamilyServiceDep,
    availability_service: AvailabilityServiceDep,
) -> AvailabilityWeekOut:
    """Nested under the family resource so ownership is the check that
    resource already performs (research.md R2-11): a parent reaches their
    own profile and each child's; a signed-in child reaches only their
    own. An unreachable profile — another account's, or a sibling's when
    the caller is a child — is a 404, not a 403, exactly as every other
    `/me/players/{profile_id}` route behaves."""
    resolved_id = await family_service.resolve_reachable_profile_id(user, profile_id)
    return await availability_service.get_week(profile_id=resolved_id)


@router.put("/{profile_id}/availability", response_model=AvailabilityWeekOut)
async def replace_player_availability(
    profile_id: str,
    body: AvailabilityWeekUpdate,
    user: PlayerParentOnlyDep,
    family_service: FamilyServiceDep,
    availability_service: AvailabilityServiceDep,
) -> AvailabilityWeekOut:
    """Same whole-week semantics as `PUT /me/availability`. A parent may
    save for their own profile and for any child's; a signed-in child may
    save only their own (FR-033) — the parent retains authority to revise
    what a child stated."""
    resolved_id = await family_service.resolve_reachable_profile_id(user, profile_id)
    return await availability_service.replace_week(body, profile_id=resolved_id)


@router.delete("/{profile_id}/availability", status_code=204)
async def clear_player_availability(
    profile_id: str,
    user: PlayerParentOnlyDep,
    family_service: FamilyServiceDep,
    availability_service: AvailabilityServiceDep,
) -> None:
    resolved_id = await family_service.resolve_reachable_profile_id(user, profile_id)
    await availability_service.clear_week(profile_id=resolved_id)
