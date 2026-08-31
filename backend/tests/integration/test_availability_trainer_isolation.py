"""US5, FR-036, SC-009, tasks.md T602 — a trainer's read of stated times
is scoped strictly to their own roster and their own Active associations;
an ended association stops disclosure immediately, and a coach cannot
reach these routes at all.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.enums import UserRole
from app.schemas.availability import AvailabilityWeekUpdate
from app.services.availability_service import AvailabilityService
from tests.helpers import (
    create_association,
    create_coach,
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def _sign_in(app_client: AsyncClient, db_session: AsyncSession, user: object) -> None:
    token = await create_session_cookie(db_session, user)  # type: ignore[arg-type]
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


async def test_another_trainers_coach_is_404_not_403(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    trainer_b, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(db_session, trainer_user_id=trainer_a.id, joined_at=utcnow())
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer_b)

    response = await app_client.get(f"/trainer/coaches/{coach.id}/availability")

    assert response.status_code == 404


async def test_a_profile_with_no_active_association_is_404_not_403(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    stranger_profile = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Not", last_name="Yours"
    )
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    response = await app_client.get(f"/trainer/players/{stranger_profile.id}/availability")

    assert response.status_code == 404


async def test_ending_an_association_makes_the_read_404_immediately(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    grace = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Grace", last_name="Family"
    )
    association = await create_association(
        db_session, trainer_id=trainer.id, player_profile_id=grace.id
    )
    await AvailabilityService(db_session).replace_week(
        AvailabilityWeekUpdate(
            slots=[{"day_of_week": 2, "start_minute": 900, "end_minute": 1020}]  # type: ignore[list-item]
        ),
        profile_id=grace.id,
    )
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    before = await app_client.get(f"/trainer/players/{grace.id}/availability")
    assert before.status_code == 200

    parent_token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", parent_token)
    ended = await app_client.delete(f"/me/players/{grace.id}/trainers/{association.id}")
    assert ended.status_code == 204

    trainer_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", trainer_token)
    after = await app_client.get(f"/trainer/players/{grace.id}/availability")

    assert after.status_code == 404


async def test_a_coach_cannot_reach_the_trainer_side_read_routes(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(db_session, trainer_user_id=trainer.id, joined_at=utcnow())
    await db_session.commit()
    await _sign_in(app_client, db_session, coach)

    coach_route = await app_client.get(f"/trainer/coaches/{coach.id}/availability")
    players_route = await app_client.get("/trainer/players")

    assert coach_route.status_code == 403
    assert players_route.status_code == 403
