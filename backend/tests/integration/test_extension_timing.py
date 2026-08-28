"""One-off timing measurements for SC-016 (join an additional trainer
within 5s) and SC-018 (context switch within 2s), recorded in
quickstart.md alongside the existing SC-006 measurement. Not part of the
regular correctness suite's assertions beyond a generous upper bound —
these are informational, run once to produce the number quickstart.md
quotes, the same way SC-006's timing check works.
"""

import time

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import (
    create_association,
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def test_sc016_accepting_a_second_trainer_completes_well_under_5s(
    app_client: AsyncClient, db_session: AsyncSession, capsys
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    trainer_b, link_b = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer_a.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    start = time.perf_counter()
    response = await app_client.post(f"/join/{link_b.code}/accept")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 5.0
    with capsys.disabled():
        print(f"\n[SC-016] accept a second trainer: {elapsed * 1000:.1f} ms")


async def test_sc018_switching_context_completes_well_under_2s(
    app_client: AsyncClient, db_session: AsyncSession, capsys
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session)
    trainer_b, _ = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer_a.id, player_profile_id=profile.id)
    await create_association(db_session, trainer_id=trainer_b.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    start = time.perf_counter()
    response = await app_client.put(
        "/me/context", json={"player_profile_id": profile.id, "trainer_id": trainer_b.id}
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 2.0
    with capsys.disabled():
        print(f"\n[SC-018] switch trainer context: {elapsed * 1000:.1f} ms")
