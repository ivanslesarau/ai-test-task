"""US2 (tasks.md T542): `POST /coach-invitations/{token}/accept` — a
signed-in account accepting an invitation (FR-012 – FR-019, FR-023)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach_invitation import CoachInvitation
from app.models.enums import UserRole
from app.models.role_details import CoachDetail
from tests.helpers import (
    create_coach,
    create_coach_invitation,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


async def test_accept_puts_the_coach_on_the_inviting_trainers_roster(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session, business_name="Harborview Hoops")
    coach = await create_coach(db_session, email="joins@example.org")
    invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="joins@example.org"
    )
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/coach-invitations/{raw_token}/accept")

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "joined"
    assert body["trainer_business_name"] == "Harborview Hoops"

    detail = await db_session.get(CoachDetail, coach.id)
    assert detail is not None
    assert detail.trainer_user_id == trainer.id
    assert detail.joined_at is not None

    row = await db_session.get(CoachInvitation, invitation.id)
    assert row is not None
    assert row.state == "accepted"
    assert row.accepted_by_user_id == coach.id


async def test_accept_from_the_wrong_address_is_403_naming_the_invited_address(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    coach = await create_coach(db_session, email="wrong-account@example.org")
    _invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="right-address@example.org"
    )
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/coach-invitations/{raw_token}/accept")

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "coach_invitation_address_mismatch"
    assert "right-address@example.org" in body["error"]["message"]


async def test_accept_by_a_non_coach_role_is_403_and_changes_no_role(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    parent = await create_user(
        db_session, role=UserRole.PLAYER_PARENT, email="a-parent@example.org"
    )
    _invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="a-parent@example.org"
    )
    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/coach-invitations/{raw_token}/accept")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "role_cannot_accept"

    await db_session.refresh(parent)
    assert parent.role == "player_parent"


async def test_reaccepting_the_same_roster_is_200_no_op_with_no_duplicate_assignment(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """FR-016."""
    trainer, _ = await create_trainer_with_link(db_session, business_name="Same Roster FC")
    from app.db.base import utcnow

    joined_at = utcnow()
    coach = await create_coach(
        db_session,
        email="already-here@example.org",
        trainer_user_id=trainer.id,
        joined_at=joined_at,
    )
    _invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="already-here@example.org"
    )
    token = await create_session_cookie(db_session, coach)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/coach-invitations/{raw_token}/accept")

    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "already_on_this_roster"
    assert body["trainer_business_name"] == "Same Roster FC"

    detail = await db_session.get(CoachDetail, coach.id)
    assert detail is not None
    assert detail.trainer_user_id == trainer.id
    # Unchanged — no new assignment was written.
    assert detail.joined_at == joined_at
