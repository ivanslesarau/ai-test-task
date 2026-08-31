"""US1 (tasks.md T519): resend, revoke, and the FR-007 duplicate guard.

`GET /coach-invitations/{token}` — the public endpoint that would return a
404 for a dead link — belongs to US2 (tasks.md T553) and is deliberately
out of this story's scope (US1 issues no such public router). Where the
task description says "the old token 404s", these tests instead assert the
invariant that response depends on: the superseded row is no longer
`CoachInvitationRepository.is_usable`.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.coach_invitation import CoachInvitation
from app.repositories.coach_invitation_repository import CoachInvitationRepository
from tests.helpers import create_session_cookie, create_trainer_with_link


async def _sign_in_trainer(db_session: AsyncSession, app_client: AsyncClient):
    trainer, _ = await create_trainer_with_link(db_session)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return trainer


async def _issue(app_client: AsyncClient, email: str) -> dict:
    response = await app_client.post("/trainer/coach-invitations", json={"email": email})
    assert response.status_code == 201
    return response.json()


async def test_resend_supersedes_and_the_list_still_shows_one_row(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)

    first = await _issue(app_client, "prospect@example.org")

    resend = await app_client.post(f"/trainer/coach-invitations/{first['id']}/resend")
    assert resend.status_code == 201
    new_body = resend.json()
    assert new_body["id"] != first["id"]
    assert new_body["invited_email"] == "prospect@example.org"
    assert new_body["state"] == "awaiting"

    old_row = await db_session.get(CoachInvitation, first["id"])
    assert old_row is not None
    assert old_row.state == "superseded"
    assert old_row.superseded_by_id == new_body["id"]
    assert CoachInvitationRepository.is_usable(old_row) is False

    listing = await app_client.get("/trainer/coach-invitations")
    assert listing.status_code == 200
    items = listing.json()["items"]
    ids = [item["id"] for item in items]
    assert first["id"] not in ids
    assert new_body["id"] in ids
    prospect_rows = [item for item in items if item["invited_email"] == "prospect@example.org"]
    assert len(prospect_rows) == 1


async def test_revoke_makes_the_invitation_unusable(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)
    issued = await _issue(app_client, "revoke-me@example.org")

    revoke = await app_client.post(f"/trainer/coach-invitations/{issued['id']}/revoke")
    assert revoke.status_code == 200
    assert revoke.json()["state"] == "revoked"

    row = await db_session.get(CoachInvitation, issued["id"])
    assert row is not None
    assert row.state == "revoked"
    assert row.revoked_at is not None
    assert CoachInvitationRepository.is_usable(row) is False


async def test_second_issue_to_a_live_address_is_409_naming_the_existing_invitation(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)
    first = await _issue(app_client, "dup@example.org")

    second = await app_client.post("/trainer/coach-invitations", json={"email": "dup@example.org"})

    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "coach_invitation_pending"
    assert body["error"]["invitation"]["id"] == first["id"]
    assert body["error"]["invitation"]["invited_email"] == "dup@example.org"


async def test_resend_of_an_accepted_row_is_422(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer = await _sign_in_trainer(db_session, app_client)
    accepted = await _issue(app_client, "accepted@example.org")

    row = await db_session.get(CoachInvitation, accepted["id"])
    assert row is not None
    row.state = "accepted"
    row.accepted_by_user_id = trainer.id
    row.accepted_at = utcnow()
    await db_session.flush()

    response = await app_client.post(f"/trainer/coach-invitations/{accepted['id']}/resend")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invitation_not_resendable"


async def test_resend_of_a_revoked_row_is_422(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)
    issued = await _issue(app_client, "revoked-twice@example.org")
    revoke = await app_client.post(f"/trainer/coach-invitations/{issued['id']}/revoke")
    assert revoke.status_code == 200

    response = await app_client.post(f"/trainer/coach-invitations/{issued['id']}/resend")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invitation_not_resendable"


async def test_revoke_of_an_already_revoked_row_is_422(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)
    issued = await _issue(app_client, "double-revoke@example.org")
    first_revoke = await app_client.post(f"/trainer/coach-invitations/{issued['id']}/revoke")
    assert first_revoke.status_code == 200

    second_revoke = await app_client.post(f"/trainer/coach-invitations/{issued['id']}/revoke")

    assert second_revoke.status_code == 422
    assert second_revoke.json()["error"]["code"] == "invitation_not_revocable"
