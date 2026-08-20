from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def _as_super_admin(app_client: AsyncClient, db_session: AsyncSession) -> AsyncClient:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return app_client


async def test_creates_a_trainer_with_business_name(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _as_super_admin(app_client, db_session)

    response = await client.post(
        "/admin/users",
        json={
            "role": "trainer",
            "email": "new-trainer@example.org",
            "first_name": "Tara",
            "last_name": "Trainer",
            "phone": "+15551234567",
            "business_name": "Elite Basketball Academy",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["status"] == "active"
    assert body["user"]["has_password"] is False
    assert body["invitation_sent"] is True


async def test_business_name_required_for_trainer_and_rejected_otherwise(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _as_super_admin(app_client, db_session)

    missing_business_name = await client.post(
        "/admin/users",
        json={
            "role": "trainer",
            "email": "trainer-no-biz@example.org",
            "first_name": "T",
            "last_name": "T",
            "phone": "+15551234567",
        },
    )
    assert missing_business_name.status_code == 422
    assert missing_business_name.json()["error"]["code"] == "validation_failed"

    unexpected_business_name = await client.post(
        "/admin/users",
        json={
            "role": "coach",
            "email": "coach-with-biz@example.org",
            "first_name": "C",
            "last_name": "C",
            "phone": "+15551234567",
            "business_name": "Should not be here",
        },
    )
    assert unexpected_business_name.status_code == 422
    assert unexpected_business_name.json()["error"]["code"] == "validation_failed"


async def test_multiple_field_errors_use_the_shared_error_envelope(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Regression test: Pydantic-level request-parsing errors (a malformed
    email, a too-short required field) are raised by FastAPI itself before
    any route body runs, through a completely different code path than the
    ValidationFailure a service raises explicitly. Without a dedicated
    RequestValidationError handler, these silently fall back to FastAPI's
    own `{"detail": [...]}` shape instead of the contract's `{"error": {...,
    "fields": [...]}}` envelope — every other 422 in the API uses the
    latter, and FR-022 requires every offending field to be identified."""
    client = await _as_super_admin(app_client, db_session)

    response = await client.post(
        "/admin/users",
        json={
            "role": "coach",
            "email": "not-an-email",
            "first_name": "",
            "last_name": "X",
            "phone": "+15551234567",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_failed"
    field_names = {f["field"] for f in body["error"]["fields"]}
    assert field_names == {"email", "first_name"}


async def test_duplicate_email_is_rejected_and_no_partial_account_remains(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _as_super_admin(app_client, db_session)
    payload = {
        "role": "coach",
        "email": "duplicate@example.org",
        "first_name": "First",
        "last_name": "Coach",
        "phone": "+15551234567",
    }

    first = await client.post("/admin/users", json=payload)
    assert first.status_code == 201

    second = await client.post("/admin/users", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "email_already_registered"


async def test_creates_coach_and_player_parent_with_no_trainer_relationship(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    client = await _as_super_admin(app_client, db_session)

    coach = await client.post(
        "/admin/users",
        json={
            "role": "coach",
            "email": "new-coach@example.org",
            "first_name": "Cody",
            "last_name": "Coach",
            "phone": "+15551234567",
        },
    )
    player_parent = await client.post(
        "/admin/users",
        json={
            "role": "player_parent",
            "email": "new-player@example.org",
            "first_name": "Pat",
            "last_name": "Player",
            "phone": "+15551234567",
        },
    )

    assert coach.status_code == 201
    assert coach.json()["user"]["role"] == "coach"
    assert player_parent.status_code == 201
    assert player_parent.json()["user"]["role"] == "player_parent"


async def test_only_super_admin_may_create_users(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(
        "/admin/users",
        json={
            "role": "trainer",
            "email": "should-not-be-created@example.org",
            "first_name": "X",
            "last_name": "Y",
            "phone": "+15551234567",
            "business_name": "Nope",
        },
    )

    assert response.status_code == 403
