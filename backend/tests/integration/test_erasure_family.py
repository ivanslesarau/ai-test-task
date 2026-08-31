"""data-model.md §30, FR-047, SC-008 (US5/family accounts, tasks.md
T420). Erasing a parent anonymizes every owned profile, cascades to
each child's sign-in account, expires live approval requests with a
null actor and clears both note fields, and leaves every association
and the directory's own aggregate numerically identical."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import ApprovalRequest
from app.models.association import TrainerPlayerAssociation
from app.models.enums import UserRole
from app.models.player_profile import PlayerProfile
from app.models.user import User
from tests.helpers import (
    create_approval_request,
    create_association,
    create_family,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def _admin_client(app_client: AsyncClient, db_session: AsyncSession) -> AsyncClient:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return app_client


async def test_erasing_a_parent_cascades_through_the_whole_family(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _admin_client(app_client, db_session)

    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    child_profile = profiles[0]
    child_account = child_accounts[0]

    trainer, link = await create_trainer_with_link(db_session, business_name="Cascade Academy")
    association = await create_association(
        db_session, trainer_id=trainer.id, player_profile_id=child_profile.id
    )

    another_trainer, another_link = await create_trainer_with_link(
        db_session, business_name="Second Academy"
    )
    request = await create_approval_request(
        db_session,
        player_profile_id=child_profile.id,
        parent_user_id=parent.id,
        trainer_user_id=another_trainer.id,
        share_link_id=another_link.id,
        parent_note="Which program?",
        child_note="The travel team.",
    )
    await db_session.commit()

    before = await client.get("/admin/users")
    total_before = before.json()["total"]

    erase = await client.post(
        f"/admin/users/{parent.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )
    assert erase.status_code == 200

    after = await client.get("/admin/users")
    assert after.json()["total"] == total_before

    # The child profile is anonymized and its sign-in link is cleared.
    refreshed_profile = await db_session.get(PlayerProfile, child_profile.id)
    assert refreshed_profile is not None
    assert refreshed_profile.first_name == "Deleted"
    assert refreshed_profile.last_name == "User"
    assert refreshed_profile.date_of_birth is None
    assert refreshed_profile.sign_in_user_id is None
    assert refreshed_profile.tokens_without_approval is False

    # The child's own sign-in account is erased too (research.md R-50).
    refreshed_child_account = await db_session.get(User, child_account.id)
    assert refreshed_child_account is not None
    assert refreshed_child_account.status == "deleted"

    # The association the child holds with their trainer is untouched —
    # neither removed nor its status changed.
    refreshed_association = await db_session.get(TrainerPlayerAssociation, association.id)
    assert refreshed_association is not None
    assert refreshed_association.status == "active"
    assert refreshed_association.trainer_user_id == trainer.id
    assert refreshed_association.player_profile_id == child_profile.id

    # The live approval request expires with no actor and both notes cleared.
    refreshed_request = await db_session.get(ApprovalRequest, request.id)
    assert refreshed_request is not None
    assert refreshed_request.status == "expired"
    assert refreshed_request.resolved_by_user_id is None
    assert refreshed_request.resolved_at is not None
    assert refreshed_request.parent_note is None
    assert refreshed_request.child_note is None


async def test_erasing_a_parent_with_a_child_who_has_no_sign_in_only_anonymizes_the_profile(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _admin_client(app_client, db_session)

    parent, profiles, _child_accounts = await create_family(
        db_session, children=1, with_sign_in=False
    )
    child_profile = profiles[0]
    await db_session.commit()

    erase = await client.post(
        f"/admin/users/{parent.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )
    assert erase.status_code == 200

    refreshed_profile = await db_session.get(PlayerProfile, child_profile.id)
    assert refreshed_profile is not None
    assert refreshed_profile.first_name == "Deleted"
    assert refreshed_profile.last_name == "User"
    assert refreshed_profile.sign_in_user_id is None


async def test_erasing_a_parent_with_no_live_requests_does_not_error(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """`expire_all_live_for_parent` is a no-op when there is nothing to
    expire — proven separately from the cascade above, since a family
    with no pending request is the common case."""
    client = await _admin_client(app_client, db_session)

    parent, _profiles, _child_accounts = await create_family(db_session, children=0)
    await db_session.commit()

    response = await client.post(
        f"/admin/users/{parent.id}/erase", json={"version": 1, "reason": "GDPR request"}
    )
    assert response.status_code == 200

    live_requests = (
        (
            await db_session.execute(
                select(ApprovalRequest).where(ApprovalRequest.parent_user_id == parent.id)
            )
        )
        .scalars()
        .all()
    )
    assert live_requests == []
