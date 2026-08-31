"""US5, FR-038, SC-011, tasks.md T604 — stated (or unstated) availability
is guidance only. Nothing in this feature blocks, refuses, or delays any
action on the grounds of a person's stated times — including a person who
has stated nothing at all.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.enums import UserRole
from tests.helpers import create_coach, create_session_cookie, create_trainer_with_link, create_user


async def _sign_in(app_client: AsyncClient, db_session: AsyncSession, user: object) -> None:
    token = await create_session_cookie(db_session, user)  # type: ignore[arg-type]
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


async def test_a_coach_with_nothing_stated_can_still_do_everything_they_can_do(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """No availability check gates a coach's ordinary actions: reading
    their own profile, updating it, and reading their own (empty) week
    all succeed exactly as they would for a coach with a full week."""
    trainer, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(db_session, trainer_user_id=trainer.id, joined_at=utcnow())
    await db_session.commit()
    await _sign_in(app_client, db_session, coach)

    own_week = await app_client.get("/me/availability")
    assert own_week.status_code == 200
    assert own_week.json() == {"slots": [], "updated_at": None}

    own_profile = await app_client.get("/me/profile")
    assert own_profile.status_code == 200

    update = await app_client.patch("/me/profile", json={"bio": "Still available for hire"})
    assert update.status_code == 200


async def test_a_trainer_can_read_and_manage_a_roster_with_nobody_having_stated_times(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A trainer's roster reads and their coach-assignment action are
    never refused, delayed, or altered because nobody on the roster has
    stated a single time — the roster and the end-assignment action both
    succeed exactly as they would with a fully populated week."""
    trainer, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(db_session, trainer_user_id=trainer.id, joined_at=utcnow())
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    roster = await app_client.get("/trainer/coaches")
    assert roster.status_code == 200
    row = next(item for item in roster.json()["items"] if item["user_id"] == coach.id)
    assert row["availability"] == []
    assert row["availability_updated_at"] is None

    ended = await app_client.delete(f"/trainer/coaches/{coach.id}")
    assert ended.status_code == 204


async def test_no_error_response_anywhere_in_this_feature_mentions_availability_as_a_reason(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A blanket proof-by-absence over every refusal this story's own
    endpoints can produce with nobody having stated a single time: not
    one carries the word "availability" as a reason for the refusal.
    Availability informs planning; it gates nothing (FR-038)."""
    trainer, _ = await create_trainer_with_link(db_session)
    other_trainer, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(db_session, trainer_user_id=trainer.id, joined_at=utcnow())
    stranger_coach = await create_user(db_session, role=UserRole.COACH)
    await db_session.commit()

    await _sign_in(app_client, db_session, other_trainer)
    responses = [
        await app_client.get(f"/trainer/coaches/{coach.id}/availability"),  # not this trainer's
        await app_client.delete(f"/trainer/coaches/{coach.id}"),  # not this trainer's
    ]
    await _sign_in(app_client, db_session, stranger_coach)
    responses.append(await app_client.get("/trainer/players"))  # wrong role

    for response in responses:
        assert response.status_code in (403, 404)
        body_text = response.text.lower()
        assert "availability" not in body_text
        assert "no times" not in body_text
