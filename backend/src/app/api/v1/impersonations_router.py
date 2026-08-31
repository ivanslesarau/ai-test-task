from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import (
    CurrentSessionRecordDep,
    ImpersonationServiceDep,
    RealAdminWithOpenImpersonationDep,
    require_roles,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.impersonation import ImpersonationCreate, ImpersonationOut, ImpersonationPage

router = APIRouter(prefix="/admin/impersonations", tags=["impersonation"])

# FR-041: enforced on the effective user, exactly like every other
# /admin route — which is also what makes FR-047's "nested impersonation
# refused" structural (research.md R2-15): while impersonating, the
# effective user cannot be a Super Admin, so this gate refuses the start
# route on its own, with no impersonation-specific code here.
SuperAdminDep = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))]


@router.get("", response_model=ImpersonationPage)
async def list_impersonations(
    admin: SuperAdminDep,
    impersonation_service: ImpersonationServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    admin_user_id: Annotated[str | None, Query()] = None,
    target_user_id: Annotated[str | None, Query()] = None,
    started_from: Annotated[datetime | None, Query()] = None,
    started_to: Annotated[datetime | None, Query()] = None,
) -> ImpersonationPage:
    """FR-053, FR-054, FR-056: Super-Admin-only, paged, and filterable by
    admin, target, and date range. Every impersonation the platform has
    ever permitted, including any still in progress."""
    _ = admin
    return await impersonation_service.history(
        admin_user_id=admin_user_id,
        target_user_id=target_user_id,
        started_from=started_from,
        started_to=started_to,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ImpersonationOut, status_code=201)
async def start_impersonation(
    body: ImpersonationCreate,
    admin: SuperAdminDep,
    session_record: CurrentSessionRecordDep,
    impersonation_service: ImpersonationServiceDep,
) -> ImpersonationOut:
    return await impersonation_service.start(
        admin=admin, target_user_id=body.user_id, session_record=session_record
    )


@router.delete("/current", status_code=204)
async def end_impersonation(
    principal: RealAdminWithOpenImpersonationDep,
    session_record: CurrentSessionRecordDep,
    impersonation_service: ImpersonationServiceDep,
) -> None:
    """research.md R2-15: authorizes on `principal.real_user` via
    `RealAdminWithOpenImpersonationDep`, never `require_roles
    (SUPER_ADMIN)` — see that dependency's docstring in `core/deps.py`."""
    assert principal.impersonation is not None  # guaranteed by the dependency
    await impersonation_service.end(
        real_user=principal.real_user,
        context=principal.impersonation,
        session_record=session_record,
    )
