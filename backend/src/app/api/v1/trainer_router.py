from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import TrainerServiceDep, require_roles
from app.models.enums import UserRole
from app.models.user import User
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
