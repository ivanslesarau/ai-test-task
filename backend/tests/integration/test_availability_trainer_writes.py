"""US5, FR-037, data-model.md §113, tasks.md T603 — a trainer's access to
stated times is strictly read-only, and reading a roster page never costs
one availability query per row.
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


async def test_no_write_method_exists_on_the_trainer_side_coach_availability_route(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(db_session, trainer_user_id=trainer.id, joined_at=utcnow())
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    path = f"/trainer/coaches/{coach.id}/availability"
    put_response = await app_client.put(path, json={"slots": []})
    post_response = await app_client.post(path, json={"slots": []})
    delete_response = await app_client.delete(path)

    assert put_response.status_code == 405
    assert post_response.status_code == 405
    assert delete_response.status_code == 405


async def test_no_write_method_exists_on_the_trainer_side_player_availability_route(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    grace = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Grace", last_name="Family"
    )
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=grace.id)
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)

    path = f"/trainer/players/{grace.id}/availability"
    put_response = await app_client.put(path, json={"slots": []})
    post_response = await app_client.post(path, json={"slots": []})
    delete_response = await app_client.delete(path)

    assert put_response.status_code == 405
    assert post_response.status_code == 405
    assert delete_response.status_code == 405


async def _count_queries_for_a_players_roster_page(
    app_client: AsyncClient, db_session: AsyncSession
) -> int:
    original_execute = db_session.execute
    count = 0

    async def _counting_execute(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        nonlocal count
        count += 1
        return await original_execute(*args, **kwargs)  # type: ignore[arg-type]

    db_session.execute = _counting_execute  # type: ignore[method-assign]
    try:
        response = await app_client.get("/trainer/players", params={"page_size": 100})
        assert response.status_code == 200
    finally:
        db_session.execute = original_execute  # type: ignore[method-assign]
    return count


async def test_a_player_roster_page_issues_one_availability_query_not_one_per_row(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Differential test: adding 24 more associated profiles must not add
    24 more queries. If availability were fetched per row, the query
    count would grow roughly linearly with the roster size; the `IN`
    query (`AvailabilityRepository.list_for_profiles`) keeps it constant
    regardless of page size (data-model.md §113, research.md R2-12)."""
    trainer, _ = await create_trainer_with_link(db_session)
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    solo_profile = await create_player_profile(
        db_session, account=parent, kind="child", first_name="Solo", last_name="Player"
    )
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=solo_profile.id)
    await AvailabilityService(db_session).replace_week(
        AvailabilityWeekUpdate(
            slots=[{"day_of_week": 0, "start_minute": 540, "end_minute": 600}]  # type: ignore[list-item]
        ),
        profile_id=solo_profile.id,
    )
    await db_session.commit()
    await _sign_in(app_client, db_session, trainer)
    one_row_count = await _count_queries_for_a_players_roster_page(app_client, db_session)

    for i in range(24):
        profile = await create_player_profile(
            db_session, account=parent, kind="child", first_name=f"Extra{i}", last_name="Player"
        )
        await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)
        await AvailabilityService(db_session).replace_week(
            AvailabilityWeekUpdate(
                slots=[{"day_of_week": 1, "start_minute": 600, "end_minute": 660}]  # type: ignore[list-item]
            ),
            profile_id=profile.id,
        )
    await db_session.commit()
    twenty_five_row_count = await _count_queries_for_a_players_roster_page(app_client, db_session)

    assert twenty_five_row_count <= one_row_count
