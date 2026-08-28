"""quickstart.md scenario 12.17 (US12, tasks.md T404, FR-157, SC-041).
A deactivated parent's pending requests cannot be resolved by anyone,
are never auto-approved, and still expire on their original schedule —
the maintenance sweep deliberately does not carry the Active-parent
guard `resolve()`'s person-driven calls do (research.md R-41's last
clause)."""

from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import RequestAlreadyResolved
from app.db.base import utcnow
from app.models.approval import ApprovalRequest
from app.models.enums import AccountStatus, ApprovalRequestStatus
from app.services.approval_service import ApprovalService
from app.services.maintenance_service import MaintenanceService
from app.services.ports.email_sender import get_email_sender
from tests.helpers import create_approval_request, create_family, create_trainer_with_link


async def test_a_deactivated_parents_pending_request_cannot_be_approved(
    db_session: AsyncSession,
) -> None:
    parent, profiles, _ = await create_family(db_session, children=1)
    trainer, link = await create_trainer_with_link(db_session, business_name="Inactive Academy")
    request = await create_approval_request(
        db_session,
        player_profile_id=profiles[0].id,
        parent_user_id=parent.id,
        trainer_user_id=trainer.id,
        share_link_id=link.id,
    )
    request_id, parent_id = request.id, parent.id
    await db_session.commit()

    parent.status = AccountStatus.INACTIVE.value
    await db_session.commit()

    settings = get_settings()
    service = ApprovalService(db_session, settings, get_email_sender(settings))

    with pytest.raises(RequestAlreadyResolved):
        await service.approve(parent_id, request_id, note=None)
    await db_session.commit()

    refreshed = await db_session.get(ApprovalRequest, request_id)
    assert refreshed is not None
    assert refreshed.status == ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value


async def test_a_deactivated_parents_request_still_expires_on_schedule(
    db_session: AsyncSession,
) -> None:
    """The complementary half: the sweep's own resolve() call
    deliberately omits `require_active_parent`, so a lapsed request tied
    to an inactive parent still expires — it is never auto-approved by
    virtue of the parent being unreachable, and it is never stuck open
    forever either (FR-157's last clause)."""
    parent, profiles, _ = await create_family(db_session, children=1)
    trainer, link = await create_trainer_with_link(
        db_session, business_name="Inactive Expiry Academy"
    )
    request = await create_approval_request(
        db_session,
        player_profile_id=profiles[0].id,
        parent_user_id=parent.id,
        trainer_user_id=trainer.id,
        share_link_id=link.id,
        requested_at=utcnow() - timedelta(hours=50),
        expires_at=utcnow() - timedelta(hours=2),
    )
    request_id = request.id
    await db_session.commit()

    parent.status = AccountStatus.INACTIVE.value
    await db_session.commit()

    settings = get_settings()
    maintenance = MaintenanceService(db_session)
    approval_service = ApprovalService(db_session, settings, get_email_sender(settings))
    expired_count = await maintenance.expire_lapsed_approval_requests(approval_service)
    await db_session.commit()

    assert expired_count == 1
    refreshed = await db_session.get(ApprovalRequest, request_id)
    assert refreshed is not None
    assert refreshed.status == ApprovalRequestStatus.EXPIRED.value
    assert refreshed.resolved_by_user_id is None
