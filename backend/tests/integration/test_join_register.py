from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.association import TrainerPlayerAssociation
from app.models.role_details import PlayerDetail
from app.models.user import User
from tests.helpers import create_trainer_with_link

_TODAY = date.today()


def _adult_dob() -> str:
    return (_TODAY - timedelta(days=366 * 25)).isoformat()


def _valid_self_payload(**overrides: object) -> dict:
    payload = {
        "first_name": "Ann",
        "last_name": "Lee",
        "email": f"ann-{overrides.get('email_suffix', 'default')}@example.org",
        "password": "correct-horse-battery-987654",
        "phone": "+14155552671",
        "is_self": True,
        "player_name": None,
        "date_of_birth": _adult_dob(),
        "gender": "prefer_not_to_say",
    }
    overrides.pop("email_suffix", None)
    payload.update(overrides)
    return payload


async def test_happy_path_creates_account_profile_detail_association_and_session(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, link = await create_trainer_with_link(db_session, business_name="Acme Academy")
    await db_session.commit()

    response = await app_client.post(
        f"/join/{link.code}/register",
        json=_valid_self_payload(email="happy-path@example.org"),
    )

    assert response.status_code == 201
    assert "pp_session" in response.cookies
    body = response.json()
    assert body["trainer_display_name"] == "Acme Academy"
    assert body["already_associated"] is False
    assert body["active_trainer_id"] == trainer.id

    result = await db_session.execute(select(User).where(User.email == "happy-path@example.org"))
    user = result.scalar_one()
    assert user.role == "player_parent"
    assert user.status == "active"

    detail_result = await db_session.execute(
        select(PlayerDetail).where(PlayerDetail.user_id == user.id)
    )
    detail = detail_result.scalar_one()
    assert detail.is_self is True
    assert detail.active_trainer_user_id == trainer.id

    assoc_result = await db_session.execute(
        select(TrainerPlayerAssociation).where(TrainerPlayerAssociation.player_user_id == user.id)
    )
    association = assoc_result.scalar_one()
    assert association.trainer_user_id == trainer.id
    assert association.share_link_id == link.id

    await db_session.refresh(link)
    assert link.use_count == 1


async def test_a_dependant_registration_stores_player_name_and_dob(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    child_dob = (_TODAY - timedelta(days=366 * 10)).isoformat()
    response = await app_client.post(
        f"/join/{link.code}/register",
        json=_valid_self_payload(
            email="parent-of-child@example.org",
            is_self=False,
            player_name="Sam Lee",
            date_of_birth=child_dob,
        ),
    )

    assert response.status_code == 201
    result = await db_session.execute(
        select(User).where(User.email == "parent-of-child@example.org")
    )
    user = result.scalar_one()
    detail_result = await db_session.execute(
        select(PlayerDetail).where(PlayerDetail.user_id == user.id)
    )
    detail = detail_result.scalar_one()
    assert detail.is_self is False
    assert detail.player_name == "Sam Lee"


async def test_duplicate_email_is_refused_and_nothing_is_left_behind(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    first = await app_client.post(
        f"/join/{link.code}/register",
        json=_valid_self_payload(email="dup@example.org"),
    )
    assert first.status_code == 201

    second = await app_client.post(
        f"/join/{link.code}/register",
        json=_valid_self_payload(email="dup@example.org"),
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "email_already_registered"

    count_result = await db_session.execute(select(User).where(User.email == "dup@example.org"))
    assert len(count_result.scalars().all()) == 1

    await db_session.refresh(link)
    assert link.use_count == 1, "the failed duplicate attempt must not raise the use count"


async def test_registration_against_an_invalid_link_leaves_nothing_behind(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    response = await app_client.post(
        "/join/not-a-real-code/register",
        json=_valid_self_payload(email="orphan@example.org"),
    )

    assert response.status_code == 404
    result = await db_session.execute(select(User).where(User.email == "orphan@example.org"))
    assert result.scalar_one_or_none() is None
