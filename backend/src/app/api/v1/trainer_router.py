from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import (
    AvailabilityServiceDep,
    CoachInvitationServiceDep,
    CoachServiceDep,
    TrainerServiceDep,
    require_roles,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.availability import AvailabilityWeekOut
from app.schemas.coach import TrainerCoachPage
from app.schemas.coach_invitation import (
    CoachInvitationCreate,
    CoachInvitationOut,
    CoachInvitationPage,
    CoachInvitationPresentedState,
)
from app.schemas.trainer_player import TrainerPlayerPage

router = APIRouter(prefix="/trainer", tags=["trainer"])

TrainerOnlyDep = Annotated[User, Depends(require_roles(UserRole.TRAINER))]


@router.get("/players", response_model=TrainerPlayerPage)
async def list_trainer_players(
    user: TrainerOnlyDep,
    trainer_service: TrainerServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> TrainerPlayerPage:
    """Scoped to the caller's own associations only — there is no
    parameter that could widen it (FR-090, SC-025)."""
    return await trainer_service.list_players(user.id, page=page, page_size=page_size, query=q)


# --- Coach invitations — trainer side (US-01.08 Story 1, FR-001 – FR-010,
# FR-023). HTTP concerns only; every business rule lives in
# CoachInvitationService (constitution Principle III).


@router.get("/coach-invitations", response_model=CoachInvitationPage)
async def list_coach_invitations(
    user: TrainerOnlyDep,
    coach_invitation_service: CoachInvitationServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    state: Annotated[CoachInvitationPresentedState | None, Query()] = None,
) -> CoachInvitationPage:
    """Scoped to the caller's own invitations only — there is no
    parameter that could widen it (FR-004, FR-009). `state` filters on
    the presented state (data-model.md §101.1); `superseded` rows are
    never returned (FR-005)."""
    return await coach_invitation_service.list_for_trainer(
        user.id, page=page, page_size=page_size, state=state
    )


@router.post("/coach-invitations", response_model=CoachInvitationOut, status_code=201)
async def issue_coach_invitation(
    body: CoachInvitationCreate,
    user: TrainerOnlyDep,
    coach_invitation_service: CoachInvitationServiceDep,
) -> CoachInvitationOut:
    """FR-001 – FR-003, FR-007, FR-008, FR-010, FR-023."""
    return await coach_invitation_service.issue(
        user, email=body.email, invitee_name=body.invitee_name, message=body.message
    )


@router.post(
    "/coach-invitations/{invitation_id}/resend",
    response_model=CoachInvitationOut,
    status_code=201,
)
async def resend_coach_invitation(
    invitation_id: str,
    user: TrainerOnlyDep,
    coach_invitation_service: CoachInvitationServiceDep,
) -> CoachInvitationOut:
    """FR-005, FR-009, FR-010, FR-023."""
    return await coach_invitation_service.resend(user, invitation_id)


@router.post("/coach-invitations/{invitation_id}/revoke", response_model=CoachInvitationOut)
async def revoke_coach_invitation(
    invitation_id: str,
    user: TrainerOnlyDep,
    coach_invitation_service: CoachInvitationServiceDep,
) -> CoachInvitationOut:
    """FR-006, FR-009, FR-023."""
    return await coach_invitation_service.revoke(user, invitation_id)


# --- Coach roster — trainer side (US2, FR-020 – FR-023). HTTP concerns
# only; every business rule lives in CoachService (Principle III).


@router.get("/coaches", response_model=TrainerCoachPage)
async def list_trainer_coaches(
    user: TrainerOnlyDep,
    coach_service: CoachServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> TrainerCoachPage:
    """Scoped to the caller's own roster only — there is no parameter
    that could widen it (FR-020, FR-034, FR-036)."""
    return await coach_service.list_roster(user.id, page=page, page_size=page_size, query=q)


@router.delete("/coaches/{coach_user_id}", status_code=204)
async def end_coach_assignment(
    coach_user_id: str,
    user: TrainerOnlyDep,
    coach_service: CoachServiceDep,
) -> None:
    """FR-021 – FR-023. A coach who is not on this trainer's roster is a
    404 — the caller is naming a resource they do not have."""
    await coach_service.end_assignment(user, coach_user_id)


# --- Availability, the trainer's read (US5, FR-034 – FR-037, FR-039).
# Read-only: no PUT/POST/DELETE exists on either path — stated times are
# the person's own (FR-037). Every business rule and the ownership check
# both live in the service layer (Principle III).


@router.get("/coaches/{coach_user_id}/availability", response_model=AvailabilityWeekOut)
async def get_coach_availability_as_trainer(
    coach_user_id: str,
    user: TrainerOnlyDep,
    coach_service: CoachServiceDep,
) -> AvailabilityWeekOut:
    """FR-034, FR-036, FR-037. Scoped to the caller's own roster; a coach
    on another trainer's roster, or on none, is a 404."""
    return await coach_service.get_availability_for_trainer(user.id, coach_user_id)


@router.get("/players/{profile_id}/availability", response_model=AvailabilityWeekOut)
async def get_player_availability_as_trainer(
    profile_id: str,
    user: TrainerOnlyDep,
    availability_service: AvailabilityServiceDep,
) -> AvailabilityWeekOut:
    """FR-034, FR-036, FR-037, FR-039. Scoped to an Active association
    between the caller and this profile, so disclosure stops the moment
    the association ends, with no separate step."""
    return await availability_service.get_week_for_profile_as_trainer(
        trainer_user_id=user.id, profile_id=profile_id
    )
