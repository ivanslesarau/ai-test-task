"""US2 (tasks.md T545): `GET /trainer/coaches` and
`DELETE /trainer/coaches/{coach_user_id}` (FR-020 – FR-023)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.role_details import CoachDetail
from tests.helpers import create_coach, create_session_cookie, create_trainer_with_link


async def test_the_roster_shows_name_address_joined_at_and_status(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    joined_at = utcnow()
    coach = await create_coach(
        db_session,
        email="on-roster@example.org",
        trainer_user_id=trainer.id,
        joined_at=joined_at,
        first_name="Ravi",
        last_name="Roster",
    )
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/trainer/coaches")

    assert response.status_code == 200
    body = response.json()
    row = next(item for item in body["items"] if item["user_id"] == coach.id)
    assert row["first_name"] == "Ravi"
    assert row["last_name"] == "Roster"
    assert row["email"] == "on-roster@example.org"
    assert row["status"] == "active"
    assert row["joined_at"] is not None
    assert row["availability"] == []
    assert row["availability_updated_at"] is None


async def test_ending_an_assignment_frees_the_coach_for_another_trainer(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    other_trainer, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(
        db_session,
        email="leaving@example.org",
        trainer_user_id=trainer.id,
        joined_at=utcnow(),
    )
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.delete(f"/trainer/coaches/{coach.id}")
    assert response.status_code == 204

    detail = await db_session.get(CoachDetail, coach.id)
    assert detail is not None
    assert detail.trainer_user_id is None
    assert detail.joined_at is None

    roster = await app_client.get("/trainer/coaches")
    assert roster.status_code == 200
    assert all(item["user_id"] != coach.id for item in roster.json()["items"])

    # The coach account and profile are untouched.
    from app.models.user import User

    fresh = await db_session.get(User, coach.id)
    assert fresh is not None
    assert fresh.status == "active"

    # And is free to accept another trainer's invitation.
    from tests.helpers import create_coach_invitation

    _invitation, raw_token = await create_coach_invitation(
        db_session, trainer=other_trainer, invited_email="leaving@example.org"
    )
    coach_token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", coach_token)

    accept = await app_client.post(f"/coach-invitations/{raw_token}/accept")
    assert accept.status_code == 200
    assert accept.json()["outcome"] == "joined"


async def test_ending_an_assignment_for_a_coach_not_on_this_roster_is_404(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    other_trainer, _ = await create_trainer_with_link(db_session)
    unrelated_coach = await create_coach(
        db_session,
        email="not-mine@example.org",
        trainer_user_id=other_trainer.id,
        joined_at=utcnow(),
    )
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.delete(f"/trainer/coaches/{unrelated_coach.id}")

    assert response.status_code == 404


async def test_a_non_trainer_cannot_reach_the_roster(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.models.enums import UserRole
    from tests.helpers import create_user

    coach = await create_user(db_session, role=UserRole.COACH, email="not-a-trainer@example.org")
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/trainer/coaches")

    assert response.status_code == 403
