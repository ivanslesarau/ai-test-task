"""data-model.md §114, FR-039 — availability's lifecycle hooks (US4, tasks.md
T589): removing a profile deletes its slots and no route returns them;
erasing an account deletes its slots; a coach's slots survive their
assignment ending."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.availability import AvailabilitySlot
from app.models.enums import UserRole
from app.models.role_details import CoachDetail
from app.models.user import User
from tests.helpers import create_player_profile, create_session_cookie, create_user


async def _sign_in(app_client: AsyncClient, db_session: AsyncSession, user: User) -> None:
    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


async def _slot_count(
    db_session: AsyncSession, *, coach_user_id: str | None = None, profile_id: str | None = None
) -> int:
    stmt = select(AvailabilitySlot)
    if coach_user_id is not None:
        stmt = stmt.where(AvailabilitySlot.coach_user_id == coach_user_id)
    else:
        stmt = stmt.where(AvailabilitySlot.player_profile_id == profile_id)
    result = await db_session.execute(stmt)
    return len(result.scalars().all())


async def test_removing_a_profile_deletes_its_slots_and_no_route_returns_them(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    child = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Riley", last_name="Family"
    )
    await db_session.commit()
    await _sign_in(app_client, db_session, parent)

    saved = await app_client.put(
        f"/me/players/{child.id}/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]},
    )
    assert saved.status_code == 200

    removed = await app_client.delete(f"/me/players/{child.id}")
    assert removed.status_code == 204

    unreachable = await app_client.get(f"/me/players/{child.id}/availability")
    assert unreachable.status_code == 404

    assert await _slot_count(db_session, profile_id=child.id) == 0


async def test_erasing_an_account_deletes_its_availability_slots(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    coach = await create_user(db_session, role=UserRole.COACH, email="cody@example.org")
    db_session.add(CoachDetail(user_id=coach.id, is_publicly_visible=False))
    await db_session.commit()

    await _sign_in(app_client, db_session, coach)
    saved = await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]},
    )
    assert saved.status_code == 200

    await _sign_in(app_client, db_session, admin)
    response = await app_client.post(
        f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )
    assert response.status_code == 200

    assert await _slot_count(db_session, coach_user_id=coach.id) == 0


async def test_a_coachs_slots_survive_their_assignment_ending(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """No code path FR-039 introduces touches `availability_slots` when
    `coach_details.trainer_user_id`/`joined_at` change — ending an
    assignment is a plain column write, not a cascade. Proven directly at
    the model layer since the assignment-ending endpoint itself belongs to
    US2 (tasks.md, a different in-flight story on this branch)."""
    coach = await create_user(db_session, role=UserRole.COACH)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    detail = CoachDetail(
        user_id=coach.id,
        is_publicly_visible=False,
        trainer_user_id=trainer.id,
        joined_at=utcnow(),
    )
    db_session.add(detail)
    await db_session.commit()
    await _sign_in(app_client, db_session, coach)

    saved = await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]},
    )
    assert saved.status_code == 200

    # Simulate ending the assignment (the two columns that make it true by
    # construction, data-model.md §102) without touching availability at
    # all.
    detail.trainer_user_id = None
    detail.joined_at = None
    await db_session.commit()

    still_there = await app_client.get("/me/availability")
    assert still_there.status_code == 200
    assert len(still_there.json()["slots"]) == 1
