"""quickstart.md §4 — a trainer's reads of stated times (US5, FR-034,
FR-035, tasks.md T601). Covers the coach and player detail reads, the
never-stated-reads-as-empty rule (never absent), and that both roster
payloads already carry the slots (research.md R2-12)."""

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


async def test_trainer_reads_a_coachs_stated_week_with_updated_at(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(db_session, trainer_user_id=trainer.id, joined_at=utcnow())
    await AvailabilityService(db_session).replace_week(
        AvailabilityWeekUpdate(
            slots=[{"day_of_week": 0, "start_minute": 1020, "end_minute": 1200}]  # type: ignore[list-item]
        ),
        coach_user_id=coach.id,
    )
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    response = await app_client.get(f"/trainer/coaches/{coach.id}/availability")

    assert response.status_code == 200
    body = response.json()
    assert body["slots"] == [{"day_of_week": 0, "start_minute": 1020, "end_minute": 1200}]
    assert body["updated_at"] is not None


async def test_trainer_reads_a_players_stated_week_with_updated_at(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    grace = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Grace", last_name="Family"
    )
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=grace.id)
    await AvailabilityService(db_session).replace_week(
        AvailabilityWeekUpdate(
            slots=[{"day_of_week": 5, "start_minute": 540, "end_minute": 720}]  # type: ignore[list-item]
        ),
        profile_id=grace.id,
    )
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    response = await app_client.get(f"/trainer/players/{grace.id}/availability")

    assert response.status_code == 200
    body = response.json()
    assert body["slots"] == [{"day_of_week": 5, "start_minute": 540, "end_minute": 720}]
    assert body["updated_at"] is not None


async def test_a_coach_with_nothing_stated_reads_empty_not_absent(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(db_session, trainer_user_id=trainer.id, joined_at=utcnow())
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    response = await app_client.get(f"/trainer/coaches/{coach.id}/availability")

    assert response.status_code == 200
    assert response.json() == {"slots": [], "updated_at": None}


async def test_a_player_with_nothing_stated_reads_empty_not_absent(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    leo = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Leo", last_name="Family"
    )
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=leo.id)
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    response = await app_client.get(f"/trainer/players/{leo.id}/availability")

    assert response.status_code == 200
    assert response.json() == {"slots": [], "updated_at": None}


async def test_the_coach_roster_row_carries_the_slots(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(db_session, trainer_user_id=trainer.id, joined_at=utcnow())
    await AvailabilityService(db_session).replace_week(
        AvailabilityWeekUpdate(
            slots=[{"day_of_week": 0, "start_minute": 1020, "end_minute": 1200}]  # type: ignore[list-item]
        ),
        coach_user_id=coach.id,
    )
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    response = await app_client.get("/trainer/coaches")

    assert response.status_code == 200
    row = next(item for item in response.json()["items"] if item["user_id"] == coach.id)
    assert row["availability"] == [{"day_of_week": 0, "start_minute": 1020, "end_minute": 1200}]
    assert row["availability_updated_at"] is not None


async def test_the_player_roster_row_carries_the_slots(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    grace = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Grace", last_name="Family"
    )
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=grace.id)
    await AvailabilityService(db_session).replace_week(
        AvailabilityWeekUpdate(
            slots=[{"day_of_week": 5, "start_minute": 540, "end_minute": 720}]  # type: ignore[list-item]
        ),
        profile_id=grace.id,
    )
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    response = await app_client.get("/trainer/players")

    assert response.status_code == 200
    row = next(item for item in response.json()["items"] if item["player_profile_id"] == grace.id)
    assert row["availability"] == [{"day_of_week": 5, "start_minute": 540, "end_minute": 720}]
    assert row["availability_updated_at"] is not None
