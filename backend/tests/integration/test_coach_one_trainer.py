"""US2 (tasks.md T543): the one-trainer rule (FR-015) and its
non-disclosure (SC-003) — a coach who already works with trainer B, and
follows trainer A's invitation, must be refused without trainer A's
response naming, hinting, or otherwise disclosing anything about trainer
B."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.coach_invitation import CoachInvitation
from tests.helpers import (
    create_coach,
    create_coach_invitation,
    create_session_cookie,
    create_trainer_with_link,
)


async def test_already_assigned_is_409_and_names_no_trainer(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session, business_name="Trainer A Academy")
    trainer_b, _ = await create_trainer_with_link(
        db_session, business_name="Trainer B Sporting Club"
    )
    coach = await create_coach(
        db_session,
        email="employed@example.org",
        trainer_user_id=trainer_b.id,
        joined_at=utcnow(),
    )
    invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer_a, invited_email="employed@example.org"
    )
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/coach-invitations/{raw_token}/accept")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "coach_already_assigned"

    # SC-003: not just "not equal to" — literally absent from the whole
    # serialized response (status line, headers, and body), by id, name,
    # and business name.
    raw_text = response.text
    assert trainer_b.id not in raw_text
    assert "Trainer B Sporting Club" not in raw_text
    for header_value in response.headers.values():
        assert trainer_b.id not in header_value
        assert "Trainer B Sporting Club" not in header_value

    row = await db_session.get(CoachInvitation, invitation.id)
    assert row is not None
    # Not spent — still `awaiting` at the storage layer.
    assert row.state == "awaiting"
    assert row.blocked_at is not None
    assert row.blocked_reason == "already_assigned"


async def test_the_invitation_remains_usable_and_the_trainer_sees_it_blocked(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    trainer_b, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(
        db_session, email="busy@example.org", trainer_user_id=trainer_b.id, joined_at=utcnow()
    )
    _invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer_a, invited_email="busy@example.org"
    )
    coach_token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", coach_token)

    blocked = await app_client.post(f"/coach-invitations/{raw_token}/accept")
    assert blocked.status_code == 409

    trainer_a_token = await create_session_cookie(db_session, trainer_a)
    await db_session.commit()
    app_client.cookies.set("pp_session", trainer_a_token)

    listing = await app_client.get("/trainer/coach-invitations")
    assert listing.status_code == 200
    items = listing.json()["items"]
    row = next(item for item in items if item["invited_email"] == "busy@example.org")
    assert row["state"] == "blocked"
    assert row["blocked_reason"] == "already_assigned"


async def test_the_block_clears_on_a_later_successful_acceptance(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    trainer_b, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(
        db_session, email="frees-up@example.org", trainer_user_id=trainer_b.id, joined_at=utcnow()
    )
    invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer_a, invited_email="frees-up@example.org"
    )
    coach_token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", coach_token)

    blocked = await app_client.post(f"/coach-invitations/{raw_token}/accept")
    assert blocked.status_code == 409

    # The coach leaves trainer B (directly, at the storage layer — the
    # end-assignment endpoint is exercised in test_coach_roster.py).
    from app.models.role_details import CoachDetail

    detail = await db_session.get(CoachDetail, coach.id)
    assert detail is not None
    detail.trainer_user_id = None
    detail.joined_at = None
    await db_session.commit()

    accepted = await app_client.post(f"/coach-invitations/{raw_token}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["outcome"] == "joined"

    row = await db_session.get(CoachInvitation, invitation.id)
    assert row is not None
    assert row.state == "accepted"
    assert row.blocked_at is None
    assert row.blocked_reason is None
