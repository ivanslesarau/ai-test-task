from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.association import TrainerPlayerAssociation
from app.models.enums import UserRole
from tests.helpers import (
    create_association,
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def test_signed_in_player_joins_a_second_trainer_with_no_new_account(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, link_a = await create_trainer_with_link(db_session, business_name="Trainer A")
    trainer_b, link_b = await create_trainer_with_link(db_session, business_name="Trainer B")
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT, email="player@example.org")
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer_a.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/join/{link_b.code}/accept")

    assert response.status_code == 200
    body = response.json()
    assert body["associated_profile_ids"] == [profile.id]
    assert body["already_associated_profile_ids"] == []
    assert body["active_trainer_id"] == trainer_b.id

    result = await db_session.execute(
        select(TrainerPlayerAssociation).where(
            TrainerPlayerAssociation.player_profile_id == profile.id
        )
    )
    associations = result.scalars().all()
    assert len(associations) == 2


async def test_repeating_the_link_returns_already_associated_without_a_duplicate(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, link = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/join/{link.code}/accept")

    assert response.status_code == 200
    body = response.json()
    assert body["associated_profile_ids"] == []
    assert body["already_associated_profile_ids"] == [profile.id]

    result = await db_session.execute(
        select(TrainerPlayerAssociation).where(
            TrainerPlayerAssociation.player_profile_id == profile.id
        )
    )
    assert len(result.scalars().all()) == 1

    await db_session.refresh(link)
    assert link.use_count == 0, "a repeat visit must not raise the link's use count"


async def test_a_coach_cannot_accept_a_player_link(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    coach = await create_user(db_session, role=UserRole.COACH)
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/join/{link.code}/accept")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "role_cannot_join"

    result = await db_session.execute(select(TrainerPlayerAssociation))
    assert result.scalars().all() == []


async def test_accepting_an_invalid_link_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post("/join/not-a-real-code/accept")
    assert response.status_code == 404


async def test_accepting_with_no_profile_on_the_account_associates_nobody(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """An account with zero player profiles — e.g. one a Super Admin
    created — has nothing to fall back to and no family member was
    named, so `_select_join_profiles` selects nobody (Story 13 scenario
    3): 200, nothing associated, nothing changes."""
    _, link = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    token = await create_session_cookie(db_session, player)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/join/{link.code}/accept")

    assert response.status_code == 200
    body = response.json()
    assert body["associated_profile_ids"] == []
    assert body["already_associated_profile_ids"] == []
    assert body["active_player_profile_id"] is None
    assert body["active_trainer_id"] is None

    result = await db_session.execute(select(TrainerPlayerAssociation))
    assert result.scalars().all() == []
