from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.join import JoinRegistrationRequest
from tests.helpers import create_trainer_with_link

_TODAY = date.today()


def _base_payload(**overrides: object) -> dict:
    payload = {
        "first_name": "Ann",
        "last_name": "Lee",
        "email": "ann@example.org",
        "password": "correct-horse-battery-987654",
        "phone": "+14155552671",
        "is_self": True,
        "player_name": None,
        "date_of_birth": (_TODAY - timedelta(days=366 * 25)).isoformat(),
        "gender": "prefer_not_to_say",
    }
    payload.update(overrides)
    return payload


async def test_self_registration_under_18_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    response = await app_client.post(
        f"/join/{link.code}/register",
        json=_base_payload(
            is_self=True,
            player_name=None,
            date_of_birth=(_TODAY - timedelta(days=366 * 12)).isoformat(),
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


async def test_dependant_registration_over_18_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    response = await app_client.post(
        f"/join/{link.code}/register",
        json=_base_payload(
            is_self=False,
            player_name="Sam Lee",
            date_of_birth=(_TODAY - timedelta(days=366 * 30)).isoformat(),
        ),
    )

    assert response.status_code == 422


async def test_dependant_registration_under_1_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    response = await app_client.post(
        f"/join/{link.code}/register",
        json=_base_payload(
            is_self=False,
            player_name="Newborn",
            date_of_birth=_TODAY.isoformat(),
        ),
    )

    assert response.status_code == 422


async def test_missing_player_name_when_not_self_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    response = await app_client.post(
        f"/join/{link.code}/register",
        json=_base_payload(
            is_self=False,
            player_name=None,
            date_of_birth=(_TODAY - timedelta(days=366 * 10)).isoformat(),
        ),
    )

    assert response.status_code == 422


async def test_player_name_supplied_when_self_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    response = await app_client.post(
        f"/join/{link.code}/register",
        json=_base_payload(is_self=True, player_name="Should not be here"),
    )

    assert response.status_code == 422


async def test_empty_optional_field_is_rejected_not_stored() -> None:
    """Principle VI: an empty string for an optional field must be a 422,
    never a stored value. player_name is the only optional string field
    on this request — its Field(min_length=1) enforces the rule when a
    caller sends "" rather than omitting the key or sending null."""
    with pytest.raises(ValidationError):
        JoinRegistrationRequest(
            first_name="Ann",
            last_name="Lee",
            email="ann@example.org",
            password="correct-horse-battery-987654",
            phone="+14155552671",
            is_self=False,
            player_name="",
            date_of_birth=(_TODAY - timedelta(days=366 * 10)),
            gender="prefer_not_to_say",
        )


async def test_malformed_email_and_missing_fields_are_all_reported(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    response = await app_client.post(
        f"/join/{link.code}/register",
        json={
            "first_name": "",
            "last_name": "Lee",
            "email": "not-an-email",
            "password": "correct-horse-battery-987654",
            "phone": "+14155552671",
            "is_self": True,
            "player_name": None,
            "date_of_birth": (_TODAY - timedelta(days=366 * 25)).isoformat(),
            "gender": "prefer_not_to_say",
        },
    )

    assert response.status_code == 422
    fields = {f["field"] for f in response.json()["error"]["fields"]}
    assert "first_name" in fields
    assert "email" in fields
