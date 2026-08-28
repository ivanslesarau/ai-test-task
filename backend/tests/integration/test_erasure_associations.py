"""FR-091, SC-008: an erased player keeps every association and appears
on each trainer's roster as "Deleted User", with participant counts
unchanged. FR-070: erasing a trainer revokes their share links."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.association import TrainerPlayerAssociation
from app.models.enums import AccountStatus, UserRole
from app.models.player_profile import PlayerProfile
from tests.helpers import (
    create_association,
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def _as_super_admin(app_client: AsyncClient, db_session: AsyncSession):
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return admin


async def test_erased_player_keeps_associations_and_appears_as_deleted_user(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, link = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)
    await db_session.commit()

    await _as_super_admin(app_client, db_session)
    erase_response = await app_client.post(
        f"/admin/users/{player.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )
    assert erase_response.status_code == 200

    trainer_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", trainer_token)

    roster = await app_client.get("/trainer/players")
    assert roster.status_code == 200
    items = roster.json()["items"]
    assert len(items) == 1
    assert items[0]["player_profile_id"] == profile.id
    assert items[0]["display_name"] == "Deleted User"


async def test_erasing_a_trainer_revokes_their_share_link(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    await _as_super_admin(app_client, db_session)
    response = await app_client.post(
        f"/admin/users/{trainer.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )
    assert response.status_code == 200

    preview = await app_client.get(f"/join/{link.code}")
    assert preview.status_code == 404


async def test_erasing_a_trainer_leaves_prior_associations_intact(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profile.id)
    await db_session.commit()

    await _as_super_admin(app_client, db_session)
    response = await app_client.post(
        f"/admin/users/{trainer.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(TrainerPlayerAssociation).where(
            TrainerPlayerAssociation.trainer_user_id == trainer.id
        )
    )
    assert result.scalar_one_or_none() is not None


async def test_erasing_a_parent_cascades_to_a_childs_sign_in(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """data-model.md §30, research.md R-38/R-50: erasing a parent must
    not leave a signed-in child able to act on behalf of an erased
    family — the child's own account is anonymized in the same
    transaction, and the profile's `sign_in_user_id` link is cleared."""
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    child_account = await create_user(
        db_session, role=UserRole.PLAYER_PARENT, first_name="Sam", last_name="Lee"
    )
    child_profile = await create_player_profile(
        db_session,
        account=parent,
        kind="child",
        first_name="Sam",
        last_name="Lee",
        sign_in_user_id=child_account.id,
    )
    await db_session.commit()

    await _as_super_admin(app_client, db_session)
    response = await app_client.post(
        f"/admin/users/{parent.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )
    assert response.status_code == 200

    await db_session.refresh(child_account)
    assert child_account.status == AccountStatus.DELETED.value
    assert child_account.email.startswith("deleted_")

    refreshed_profile = await db_session.get(PlayerProfile, child_profile.id)
    assert refreshed_profile is not None
    assert refreshed_profile.sign_in_user_id is None
    # A child's name is not NULLed — the roster must still read "Deleted
    # User" (FR-091, ck_player_profiles_self_names).
    assert refreshed_profile.first_name == "Deleted"
    assert refreshed_profile.last_name == "User"
