"""US2 (tasks.md T541): `POST /coach-invitations/{token}/register` —
establishing a brand-new coach account through an invitation and joining
the inviting trainer's roster in the same request (FR-011, FR-013, FR-017,
FR-018, FR-023)."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach_invitation import CoachInvitation
from app.models.role_details import CoachDetail
from app.models.user import User
from tests.helpers import KNOWN_PASSWORD, create_coach_invitation, create_trainer_with_link


async def test_register_creates_a_coach_on_the_roster_and_signs_in(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session, business_name="Rising Stars FC")
    invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="new-coach@example.org"
    )
    await db_session.commit()

    response = await app_client.post(
        f"/coach-invitations/{raw_token}/register",
        json={
            "first_name": "Nadia",
            "last_name": "Newcoach",
            "password": KNOWN_PASSWORD,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["outcome"] == "joined"
    assert body["trainer_business_name"] == "Rising Stars FC"
    assert "pp_session" in response.cookies

    user = (
        await db_session.execute(select(User).where(User.email == "new-coach@example.org"))
    ).scalar_one()
    assert user.role == "coach"

    detail = await db_session.get(CoachDetail, user.id)
    assert detail is not None
    assert detail.trainer_user_id == trainer.id
    assert detail.joined_at is not None

    row = await db_session.get(CoachInvitation, invitation.id)
    assert row is not None
    assert row.state == "accepted"
    assert row.accepted_by_user_id == user.id
    assert row.accepted_at is not None


async def test_register_takes_email_role_and_trainer_from_the_invitation_only(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A malicious body naming a different email, role, or trainer has
    nothing to act on — `CoachRegistrationRequest` carries no such
    fields at all, so an attempt to smuggle them through unknown keys is
    a 422 (the schema forbids extra fields)."""
    trainer, _ = await create_trainer_with_link(db_session)
    _invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="bound-address@example.org"
    )
    await db_session.commit()

    response = await app_client.post(
        f"/coach-invitations/{raw_token}/register",
        json={
            "first_name": "Sly",
            "last_name": "Attacker",
            "password": KNOWN_PASSWORD,
            "email": "attacker-chosen@example.org",
            "role": "super_admin",
            "trainer_id": "not-a-real-trainer",
        },
    )

    assert response.status_code == 422

    still_registerable = await app_client.post(
        f"/coach-invitations/{raw_token}/register",
        json={"first_name": "Sly", "last_name": "Attacker", "password": KNOWN_PASSWORD},
    )
    assert still_registerable.status_code == 201
    user = (
        await db_session.execute(select(User).where(User.email == "bound-address@example.org"))
    ).scalar_one()
    assert user.role == "coach"


async def test_register_is_409_when_an_account_already_exists_at_the_invited_address(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    from app.models.enums import UserRole
    from tests.helpers import create_user

    await create_user(db_session, role=UserRole.COACH, email="already-here@example.org")
    _invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="already-here@example.org"
    )
    await db_session.commit()

    response = await app_client.post(
        f"/coach-invitations/{raw_token}/register",
        json={"first_name": "Late", "last_name": "Comer", "password": KNOWN_PASSWORD},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_registered"


async def test_register_with_a_dead_link_is_404(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    response = await app_client.post(
        "/coach-invitations/not-a-real-token-not-a-real-token-xyz/register",
        json={"first_name": "Nobody", "last_name": "Home", "password": KNOWN_PASSWORD},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "invitation_link_invalid"
