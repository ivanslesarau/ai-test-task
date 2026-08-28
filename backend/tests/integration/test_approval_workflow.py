"""quickstart.md Story 12 scenarios 12.1-12.12 and 12.18 (US12, tasks.md
T399). The whole Pending Parent Approval workflow, driven end to end by
the join-a-trainer requests Family Phase C raises."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.approval import ApprovalRequest
from app.models.audit import AuditEntry
from app.models.user import User
from tests.helpers import create_family, create_session_cookie, create_trainer_with_link
from tests.integration.test_child_join_block import _outbox_messages_mentioning


async def _raise_join_request(
    app_client: AsyncClient,
    db_session: AsyncSession,
    *,
    child_token: str,
    parent_token: str,
    business_name: str,
) -> tuple[str, str]:
    """Follows a fresh trainer's link as the child, which is blocked and
    raises a live `join_trainer` request (US11). Returns
    `(request_id, trainer_id)` and leaves the client authenticated as the
    parent."""
    trainer, link = await create_trainer_with_link(db_session, business_name=business_name)
    await db_session.commit()

    app_client.cookies.set("pp_session", child_token)
    response = await app_client.post(f"/join/{link.code}/accept")
    await db_session.commit()
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "child_must_ask_parent"

    result = await db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.trainer_user_id == trainer.id)
    )
    request = result.scalar_one()

    app_client.cookies.set("pp_session", parent_token)
    return request.id, trainer.id


async def test_the_full_approval_workflow(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    await db_session.commit()
    child_profile = profiles[0]
    child_token = await create_session_cookie(db_session, child_accounts[0])
    parent_token = await create_session_cookie(db_session, parent)
    await db_session.commit()

    # 12.1 — the child's own view before anyone decides.
    request_id, trainer_id = await _raise_join_request(
        app_client,
        db_session,
        child_token=child_token,
        parent_token=parent_token,
        business_name="Workflow Academy One",
    )
    app_client.cookies.set("pp_session", child_token)
    own_requests = await app_client.get("/me/requests")
    assert own_requests.status_code == 200
    items = own_requests.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "pending_parent_approval"

    # 12.2 — the parent's queue names the child, what is asked, and expires_at.
    app_client.cookies.set("pp_session", parent_token)
    approvals = await app_client.get("/me/approvals")
    assert approvals.status_code == 200
    queue_entry = approvals.json()["items"][0]
    assert queue_entry["id"] == request_id
    assert queue_entry["player_display_name"]
    assert queue_entry["trainer_display_name"] == "Workflow Academy One"
    assert queue_entry["expires_at"]

    # 12.3 — an email to the parent, and a pending count in the nav frame's data.
    settings = get_settings()
    matches = _outbox_messages_mentioning(
        settings.email_outbox_dir, parent.email, "Workflow Academy One"
    )
    assert len(matches) == 1

    # 12.4 — approve: 200, and the child is associated with the trainer.
    approved = await app_client.post(f"/me/approvals/{request_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    trainer = await db_session.get(User, trainer_id)
    assert trainer is not None
    roster_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", roster_token)
    roster = await app_client.get("/trainer/players")
    assert roster.status_code == 200
    assert any(p["player_profile_id"] == child_profile.id for p in roster.json()["items"])

    # 12.5 — the child sees the resolved status.
    app_client.cookies.set("pp_session", child_token)
    own_requests_after = await app_client.get("/me/requests")
    resolved_item = next(
        i for i in own_requests_after.json()["items"] if i["id"] == request_id
    )
    assert resolved_item["status"] == "approved"

    # 12.6 — approving the same request again is refused, not repeated.
    app_client.cookies.set("pp_session", parent_token)
    second_approve = await app_client.post(f"/me/approvals/{request_id}/approve")
    assert second_approve.status_code == 409
    assert second_approve.json()["error"]["code"] == "request_already_resolved"

    # 12.7 — raise a second request, deny it with a note.
    deny_request_id, _ = await _raise_join_request(
        app_client,
        db_session,
        child_token=child_token,
        parent_token=parent_token,
        business_name="Workflow Academy Two",
    )
    denied = await app_client.post(
        f"/me/approvals/{deny_request_id}/deny", json={"note": "Not this season."}
    )
    assert denied.status_code == 200
    assert denied.json()["status"] == "denied"

    app_client.cookies.set("pp_session", child_token)
    denied_list = await app_client.get("/me/requests", params={"status": "denied"})
    assert denied_list.status_code == 200
    denied_view = next(i for i in denied_list.json()["items"] if i["id"] == deny_request_id)
    assert denied_view["parent_note"] == "Not this season."

    # 12.8 — raise a third request, ask for information: expires_at unchanged.
    app_client.cookies.set("pp_session", parent_token)
    info_request_id, _ = await _raise_join_request(
        app_client,
        db_session,
        child_token=child_token,
        parent_token=parent_token,
        business_name="Workflow Academy Three",
    )
    before_info = await app_client.get(f"/me/approvals/{info_request_id}")
    expires_before = before_info.json()["expires_at"]

    info_requested = await app_client.post(
        f"/me/approvals/{info_request_id}/request-info", json={"note": "Which program?"}
    )
    assert info_requested.status_code == 200
    assert info_requested.json()["status"] == "info_requested"
    assert info_requested.json()["expires_at"] == expires_before

    # 12.9 — the child responds: back to pending, child_note set, deadline unchanged.
    app_client.cookies.set("pp_session", child_token)
    responded = await app_client.post(
        f"/me/requests/{info_request_id}/respond", json={"note": "The travel team."}
    )
    assert responded.status_code == 200
    assert responded.json()["status"] == "pending_parent_approval"
    assert responded.json()["child_note"] == "The travel team."
    assert responded.json()["expires_at"] == expires_before

    # 12.10 — the child withdraws a pending request.
    withdraw_request_id, _ = await _raise_join_request(
        app_client,
        db_session,
        child_token=child_token,
        parent_token=parent_token,
        business_name="Workflow Academy Four",
    )
    app_client.cookies.set("pp_session", child_token)
    withdrawn = await app_client.post(f"/me/requests/{withdraw_request_id}/withdraw")
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"

    app_client.cookies.set("pp_session", parent_token)
    queue_after_withdrawal = await app_client.get("/me/approvals")
    assert all(
        item["id"] != withdraw_request_id for item in queue_after_withdrawal.json()["items"]
    )

    # 12.11 — the child cannot approve their own request.
    fifth_request_id, _ = await _raise_join_request(
        app_client,
        db_session,
        child_token=child_token,
        parent_token=parent_token,
        business_name="Workflow Academy Five",
    )
    app_client.cookies.set("pp_session", child_token)
    child_approve_attempt = await app_client.post(f"/me/approvals/{fifth_request_id}/approve")
    assert child_approve_attempt.status_code == 403

    # 12.18 — the audit trail names the child profile, request, decision, actor, time.
    audit_rows = (
        (
            await db_session.execute(
                select(AuditEntry).where(AuditEntry.action == "approval_approved")
            )
        )
        .scalars()
        .all()
    )
    approved_entry = next(e for e in audit_rows if request_id in (e.detail or ""))
    assert approved_entry.actor_user_id == parent.id
    assert child_profile.id in (approved_entry.detail or "")

    denied_audit = (
        (
            await db_session.execute(
                select(AuditEntry).where(AuditEntry.action == "approval_denied")
            )
        )
        .scalars()
        .all()
    )
    denied_entry = next(e for e in denied_audit if deny_request_id in (e.detail or ""))
    assert denied_entry.actor_user_id == parent.id


async def test_a_child_cannot_bypass_a_pending_request_by_calling_join_directly(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """12.12: the request is not a suggestion — the direct join endpoint
    still refuses the child while a request waits (FR-144, FR-133)."""
    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    trainer, link = await create_trainer_with_link(db_session, business_name="Bypass Academy")
    await db_session.commit()

    child_token = await create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", child_token)

    first = await app_client.post(f"/join/{link.code}/accept")
    await db_session.commit()
    assert first.status_code == 403

    second = await app_client.post(f"/join/{link.code}/accept")
    assert second.status_code == 403
    assert second.json()["error"]["code"] == "child_must_ask_parent"
