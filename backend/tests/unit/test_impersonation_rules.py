"""US6 (tasks.md T613): who may impersonate whom (FR-042), and the
end-reason selection `get_principal` performs on every request
(FR-042 vs FR-050, research.md R2-19) — both pure functions, exercised
here with no `db_session` at all.
"""

from datetime import timedelta

import pytest

from app.core.errors import ImpersonationNotPermitted
from app.db.base import new_uuid, utcnow
from app.models.enums import AccountStatus, ImpersonationEndReason, UserRole
from app.models.impersonation import ImpersonationSession
from app.models.user import User
from app.services.impersonation_service import ImpersonationService


def _user(*, role: UserRole, status: AccountStatus = AccountStatus.ACTIVE) -> User:
    now = utcnow()
    return User(
        id=new_uuid(),
        email=f"{role.value}-{new_uuid()}@example.org",
        role=role.value,
        status=status.value,
        version=1,
        created_at=now,
        updated_at=now,
    )


def _record(
    *,
    admin_id: str,
    target_id: str,
    target_status_at_start: AccountStatus = AccountStatus.ACTIVE,
    started_at: object | None = None,
    expires_at: object | None = None,
) -> ImpersonationSession:
    now = utcnow()
    return ImpersonationSession(
        id=new_uuid(),
        admin_user_id=admin_id,
        target_user_id=target_id,
        auth_session_id=new_uuid(),
        target_status_at_start=target_status_at_start.value,
        started_at=started_at or now,
        expires_at=expires_at or (now + timedelta(minutes=60)),
    )


# --- check_start_permitted (FR-042) -----------------------------------------


def test_a_trainer_may_be_impersonated() -> None:
    admin = _user(role=UserRole.SUPER_ADMIN)
    target = _user(role=UserRole.TRAINER)
    ImpersonationService.check_start_permitted(admin_id=admin.id, target=target)


def test_a_coach_may_be_impersonated() -> None:
    admin = _user(role=UserRole.SUPER_ADMIN)
    target = _user(role=UserRole.COACH)
    ImpersonationService.check_start_permitted(admin_id=admin.id, target=target)


def test_a_player_parent_may_be_impersonated() -> None:
    admin = _user(role=UserRole.SUPER_ADMIN)
    target = _user(role=UserRole.PLAYER_PARENT)
    ImpersonationService.check_start_permitted(admin_id=admin.id, target=target)


def test_an_inactive_target_is_permitted() -> None:
    admin = _user(role=UserRole.SUPER_ADMIN)
    target = _user(role=UserRole.TRAINER, status=AccountStatus.INACTIVE)
    ImpersonationService.check_start_permitted(admin_id=admin.id, target=target)


def test_another_super_admin_cannot_be_impersonated() -> None:
    admin = _user(role=UserRole.SUPER_ADMIN)
    target = _user(role=UserRole.SUPER_ADMIN)
    with pytest.raises(ImpersonationNotPermitted):
        ImpersonationService.check_start_permitted(admin_id=admin.id, target=target)


def test_the_caller_cannot_impersonate_themselves() -> None:
    admin = _user(role=UserRole.SUPER_ADMIN)
    with pytest.raises(ImpersonationNotPermitted):
        ImpersonationService.check_start_permitted(admin_id=admin.id, target=admin)


def test_an_erased_account_cannot_be_impersonated() -> None:
    admin = _user(role=UserRole.SUPER_ADMIN)
    target = _user(role=UserRole.TRAINER, status=AccountStatus.DELETED)
    with pytest.raises(ImpersonationNotPermitted):
        ImpersonationService.check_start_permitted(admin_id=admin.id, target=target)


# --- select_auto_end_reason (FR-042 vs FR-050, research.md R2-19) ----------


def test_past_the_deadline_is_timed_out_regardless_of_target_status() -> None:
    admin_id, target_id = new_uuid(), new_uuid()
    record = _record(
        admin_id=admin_id, target_id=target_id, expires_at=utcnow() - timedelta(seconds=1)
    )
    target = _user(role=UserRole.TRAINER)
    reason = ImpersonationService.select_auto_end_reason(record, target, now=utcnow())
    assert reason is ImpersonationEndReason.TIMED_OUT


def test_a_deleted_target_is_target_erased() -> None:
    admin_id, target_id = new_uuid(), new_uuid()
    record = _record(admin_id=admin_id, target_id=target_id)
    target = _user(role=UserRole.TRAINER, status=AccountStatus.DELETED)
    reason = ImpersonationService.select_auto_end_reason(record, target, now=utcnow())
    assert reason is ImpersonationEndReason.TARGET_ERASED


def test_a_missing_target_is_target_erased() -> None:
    """A `None` target — the account row is gone — resolves the same as a
    `DELETED` one; the platform never hard-deletes a `users` row, but the
    resolver treats the two identically as defence in depth."""
    admin_id, target_id = new_uuid(), new_uuid()
    record = _record(admin_id=admin_id, target_id=target_id)
    reason = ImpersonationService.select_auto_end_reason(record, None, now=utcnow())
    assert reason is ImpersonationEndReason.TARGET_ERASED


def test_a_target_that_leaves_active_status_is_target_deactivated() -> None:
    admin_id, target_id = new_uuid(), new_uuid()
    record = _record(
        admin_id=admin_id, target_id=target_id, target_status_at_start=AccountStatus.ACTIVE
    )
    target = _user(role=UserRole.TRAINER, status=AccountStatus.INACTIVE)
    reason = ImpersonationService.select_auto_end_reason(record, target, now=utcnow())
    assert reason is ImpersonationEndReason.TARGET_DEACTIVATED


def test_a_target_inactive_at_start_and_still_inactive_does_not_end() -> None:
    """research.md R2-19's central subtlety: FR-050 ends a session when
    the target "leaves Active status" — an account that was never Active
    to begin with cannot leave it."""
    admin_id, target_id = new_uuid(), new_uuid()
    record = _record(
        admin_id=admin_id, target_id=target_id, target_status_at_start=AccountStatus.INACTIVE
    )
    target = _user(role=UserRole.TRAINER, status=AccountStatus.INACTIVE)
    reason = ImpersonationService.select_auto_end_reason(record, target, now=utcnow())
    assert reason is None


def test_a_target_still_active_does_not_end() -> None:
    admin_id, target_id = new_uuid(), new_uuid()
    record = _record(
        admin_id=admin_id, target_id=target_id, target_status_at_start=AccountStatus.ACTIVE
    )
    target = _user(role=UserRole.TRAINER, status=AccountStatus.ACTIVE)
    reason = ImpersonationService.select_auto_end_reason(record, target, now=utcnow())
    assert reason is None
