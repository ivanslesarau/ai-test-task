"""quickstart.md scenarios 12.15 and 12.16 (US12, tasks.md T403, SC-034).
Against an injected clock (a request created already past its deadline,
never an actual two-day wait): a lapsed request is unapprovable before
the sweep runs, because `ApprovalRepository.resolve`'s predicate checks
`expires_at` on every attempt, and `expired` with both parties notified
after it runs (research.md R-41, R-43)."""

import glob
from datetime import timedelta
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import utcnow
from app.models.approval import ApprovalRequest
from app.models.enums import ApprovalRequestStatus
from app.models.user import User
from app.services.approval_service import ApprovalService
from app.services.maintenance_service import MaintenanceService
from app.services.ports.email_sender import get_email_sender
from tests.helpers import (
    create_approval_request,
    create_family,
    create_session_cookie,
    create_trainer_with_link,
)


def _outbox_messages_mentioning(outbox_dir: str, *needles: str) -> list[str]:
    matches = []
    for path in glob.glob(f"{outbox_dir}/*.txt"):
        content = Path(path).read_text(encoding="utf-8")
        if all(needle in content for needle in needles):
            matches.append(content)
    return matches


async def test_a_lapsed_request_is_unapprovable_before_the_sweep_and_expired_after_it(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    trainer, link = await create_trainer_with_link(db_session, business_name="Lapsed Academy")
    request = await create_approval_request(
        db_session,
        player_profile_id=profiles[0].id,
        parent_user_id=parent.id,
        trainer_user_id=trainer.id,
        share_link_id=link.id,
        requested_at=utcnow() - timedelta(hours=50),
        expires_at=utcnow() - timedelta(hours=2),
    )
    # Captured before the 409 attempt below: it is resolved inside the
    # same SAVEPOINT `approve()` opens for a successful decision, so its
    # rollback expires every object this session has loaded — a bare
    # attribute access afterward needs a synchronous reload AsyncSession
    # cannot do (SQLAlchemy's MissingGreenlet).
    request_id = request.id
    parent_email = parent.email
    child_account_id = child_accounts[0].id
    await db_session.commit()

    # 12.16 — already unapprovable before the sweep ever runs: the
    # predicate, not the sweep, is what makes this true.
    parent_token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", parent_token)
    early_attempt = await app_client.post(f"/me/approvals/{request_id}/approve")
    await db_session.commit()
    assert early_attempt.status_code == 409

    refreshed = await db_session.get(ApprovalRequest, request_id)
    assert refreshed is not None
    assert refreshed.status == ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value

    # 12.15 — run the sweep: expired, not associated, both parties notified.
    settings = get_settings()
    maintenance = MaintenanceService(db_session)
    approval_service = ApprovalService(db_session, settings, get_email_sender(settings))
    expired_count = await maintenance.expire_lapsed_approval_requests(approval_service)
    await db_session.commit()
    assert expired_count == 1

    after_sweep = await db_session.get(ApprovalRequest, request_id)
    assert after_sweep is not None
    assert after_sweep.status == ApprovalRequestStatus.EXPIRED.value
    assert after_sweep.resolved_by_user_id is None
    assert after_sweep.resolved_at is not None

    outbox_dir = settings.email_outbox_dir
    assert len(_outbox_messages_mentioning(outbox_dir, parent_email, "Lapsed Academy")) >= 1
    child_account = await db_session.get(User, child_account_id)
    assert child_account is not None
    assert len(_outbox_messages_mentioning(outbox_dir, child_account.email)) >= 1


async def test_an_information_exchange_does_not_restart_the_expiry_deadline(
    db_session: AsyncSession,
) -> None:
    """The `info_requested` branch of the same rule: a request the parent
    asked a question about still expires on its original schedule, never
    granted extra time by the exchange (FR-155's last clause)."""
    parent, profiles, _ = await create_family(db_session, children=1)
    trainer, link = await create_trainer_with_link(
        db_session, business_name="Info Exchange Academy"
    )
    request = await create_approval_request(
        db_session,
        player_profile_id=profiles[0].id,
        parent_user_id=parent.id,
        trainer_user_id=trainer.id,
        share_link_id=link.id,
        status=ApprovalRequestStatus.INFO_REQUESTED,
        parent_note="Which program?",
        child_note="The travel team.",
        requested_at=utcnow() - timedelta(hours=50),
        expires_at=utcnow() - timedelta(hours=1),
    )
    await db_session.commit()

    settings = get_settings()
    maintenance = MaintenanceService(db_session)
    approval_service = ApprovalService(db_session, settings, get_email_sender(settings))
    expired_count = await maintenance.expire_lapsed_approval_requests(approval_service)
    await db_session.commit()

    assert expired_count == 1
    refreshed = await db_session.get(ApprovalRequest, request.id)
    assert refreshed is not None
    assert refreshed.status == ApprovalRequestStatus.EXPIRED.value
