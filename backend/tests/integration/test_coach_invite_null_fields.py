"""US1 (tasks.md T521): the constitution's field-clearing gate (Principle
VI) for `invitee_name`/`message` on `POST /trainer/coach-invitations`.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach_invitation import CoachInvitation
from tests.helpers import create_session_cookie, create_trainer_with_link


async def _sign_in_trainer(db_session: AsyncSession, app_client: AsyncClient) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


async def test_explicit_null_persists_as_sql_null(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)

    response = await app_client.post(
        "/trainer/coach-invitations",
        json={"email": "explicit-null@example.org", "invitee_name": None, "message": None},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["invitee_name"] is None
    assert body["message"] is None

    row = await db_session.get(CoachInvitation, body["id"])
    assert row is not None
    assert row.invitee_name is None
    assert row.message is None


async def test_omitted_keys_default_to_null(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)

    response = await app_client.post(
        "/trainer/coach-invitations", json={"email": "omitted@example.org"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["invitee_name"] is None
    assert body["message"] is None

    row = await db_session.get(CoachInvitation, body["id"])
    assert row is not None
    assert row.invitee_name is None
    assert row.message is None


async def test_empty_string_invitee_name_is_422_not_persisted(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)

    response = await app_client.post(
        "/trainer/coach-invitations",
        json={"email": "empty-name@example.org", "invitee_name": ""},
    )

    assert response.status_code == 422


async def test_empty_string_message_is_422_not_persisted(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)

    response = await app_client.post(
        "/trainer/coach-invitations",
        json={"email": "empty-message@example.org", "message": ""},
    )

    assert response.status_code == 422


async def test_a_real_value_persists_unchanged(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)

    response = await app_client.post(
        "/trainer/coach-invitations",
        json={
            "email": "real-value@example.org",
            "invitee_name": "Sam Coach",
            "message": "Welcome to the team!",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["invitee_name"] == "Sam Coach"
    assert body["message"] == "Welcome to the team!"
