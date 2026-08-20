from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import ErasureServiceDep, UserAdminServiceDep, require_roles
from app.models.enums import AccountStatus, UserRole
from app.models.user import User
from app.schemas.admin_user import (
    AuditEntryOut,
    CreatedUser,
    CreateUserRequest,
    EraseUserRequest,
    ErasureRecordOut,
    StatusChangeRequest,
    UserDetail,
    UserSummary,
)
from app.schemas.common import Page

router = APIRouter(prefix="/admin", tags=["admin-users"])

# Every route in this router is Super-Admin-only (FR-016, FR-051).
SuperAdminDep = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))]


@router.post("/users", response_model=CreatedUser, status_code=201)
async def create_user(
    body: CreateUserRequest, admin_service: UserAdminServiceDep, actor: SuperAdminDep
) -> CreatedUser:
    return await admin_service.create_user(
        role=body.role,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
        business_name=body.business_name,
        actor=actor,
    )


@router.get("/users", response_model=Page[UserSummary])
async def list_users(
    admin_service: UserAdminServiceDep,
    _actor: SuperAdminDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    q: Annotated[str | None, Query(max_length=200)] = None,
    role: UserRole | None = None,
    status: AccountStatus | None = None,
    sort: str = "created_at_desc",
) -> Page[UserSummary]:
    items, total = await admin_service.list_users(
        page=page, page_size=page_size, query=q, role=role, status=status, sort=sort
    )
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.get("/users/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: str, admin_service: UserAdminServiceDep, _actor: SuperAdminDep
) -> UserDetail:
    return await admin_service.get_user(user_id)


@router.post("/users/{user_id}/deactivate", response_model=UserDetail)
async def deactivate_user(
    user_id: str,
    body: StatusChangeRequest,
    admin_service: UserAdminServiceDep,
    actor: SuperAdminDep,
) -> UserDetail:
    return await admin_service.deactivate(user_id, actor=actor, expected_version=body.version)


@router.post("/users/{user_id}/reactivate", response_model=UserDetail)
async def reactivate_user(
    user_id: str,
    body: StatusChangeRequest,
    admin_service: UserAdminServiceDep,
    actor: SuperAdminDep,
) -> UserDetail:
    return await admin_service.reactivate(user_id, actor=actor, expected_version=body.version)


@router.post("/users/{user_id}/reinvite")
async def reinvite_user(
    user_id: str, admin_service: UserAdminServiceDep, actor: SuperAdminDep
) -> dict[str, object]:
    invitation_sent, expires_at = await admin_service.reinvite(user_id, actor=actor)
    return {"invitation_sent": invitation_sent, "expires_at": expires_at}


@router.get("/users/{user_id}/audit", response_model=Page[AuditEntryOut])
async def list_user_audit(
    user_id: str,
    admin_service: UserAdminServiceDep,
    _actor: SuperAdminDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Page[AuditEntryOut]:
    items, total = await admin_service.list_audit(user_id, page=page, page_size=page_size)
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.post("/users/{user_id}/erase", response_model=UserDetail)
async def erase_user(
    user_id: str,
    body: EraseUserRequest,
    erasure_service: ErasureServiceDep,
    actor: SuperAdminDep,
) -> UserDetail:
    return await erasure_service.erase(
        user_id, actor=actor, expected_version=body.version, reason=body.reason
    )


@router.get("/erasure-records/{user_id}", response_model=ErasureRecordOut)
async def get_erasure_record(
    user_id: str, erasure_service: ErasureServiceDep, _actor: SuperAdminDep
) -> ErasureRecordOut:
    return await erasure_service.get_erasure_record(user_id)
