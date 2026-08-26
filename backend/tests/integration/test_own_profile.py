import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.role_details import CoachDetail, ParentContact, PlayerDetail, TrainerOrganization
from tests.helpers import create_session_cookie, create_user


async def _sign_in(app_client: AsyncClient, db_session: AsyncSession, role: UserRole):
    user = await create_user(db_session, role=role)
    if role is UserRole.TRAINER:
        db_session.add(TrainerOrganization(user_id=user.id, business_name="Acme Training"))
    elif role is UserRole.COACH:
        db_session.add(CoachDetail(user_id=user.id, is_publicly_visible=False))
    elif role is UserRole.PLAYER_PARENT:
        db_session.add(PlayerDetail(user_id=user.id))
        db_session.add(ParentContact(user_id=user.id))
    await db_session.flush()

    token = await create_session_cookie(db_session, user)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return user


@pytest.mark.parametrize(
    "role",
    [UserRole.SUPER_ADMIN, UserRole.TRAINER, UserRole.COACH, UserRole.PLAYER_PARENT],
)
async def test_get_own_profile_returns_role_appropriate_editable_fields(
    app_client: AsyncClient, db_session: AsyncSession, role: UserRole
) -> None:
    await _sign_in(app_client, db_session, role)

    response = await app_client.get("/me/profile")

    assert response.status_code == 200
    body = response.json()
    assert {"first_name", "last_name", "phone"} <= set(body["editable_fields"])
    assert "skill_level" not in body["editable_fields"]


async def test_partial_update_persists_common_fields(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in(app_client, db_session, UserRole.COACH)

    response = await app_client.patch(
        "/me/profile", json={"first_name": "Updated", "phone": "+14155552671"}
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"
    assert response.json()["phone"] == "+14155552671"

    reread = await app_client.get("/me/profile")
    assert reread.json()["first_name"] == "Updated"


@pytest.mark.parametrize("field", ["email", "role", "status", "created_at", "skill_level"])
async def test_identity_fields_are_rejected_not_ignored(
    app_client: AsyncClient, db_session: AsyncSession, field: str
) -> None:
    await _sign_in(app_client, db_session, UserRole.PLAYER_PARENT)
    value = "2026-01-01T00:00:00" if field == "created_at" else "hacked-value"

    response = await app_client.patch("/me/profile", json={field: value})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert any(f["field"] == field for f in response.json()["error"]["fields"])


async def test_coach_cannot_write_a_player_only_field(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in(app_client, db_session, UserRole.COACH)

    response = await app_client.patch("/me/profile", json={"jersey_number": "07"})

    assert response.status_code == 422


async def test_trainer_can_update_business_detail(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in(app_client, db_session, UserRole.TRAINER)

    response = await app_client.patch(
        "/me/profile", json={"business_name": "New Name", "website": "https://example.org"}
    )

    assert response.status_code == 200
    assert response.json()["role_detail"]["business_name"] == "New Name"


@pytest.mark.parametrize(
    "field",
    [
        "phone",
        "school",
        "jersey_number",
        "emergency_contact_name",
        "emergency_contact_phone",
        "emergency_contact_relation",
    ],
)
async def test_empty_string_for_a_nullable_field_is_rejected_with_422(
    app_client: AsyncClient, db_session: AsyncSession, field: str
) -> None:
    """Constitution Principle VI, storage invariant: no nullable text
    column may hold ''. A field-attributed 422 is the expected response,
    not a silently persisted empty string."""
    await _sign_in(app_client, db_session, UserRole.PLAYER_PARENT)

    response = await app_client.patch("/me/profile", json={field: ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert any(f["field"] == field for f in response.json()["error"]["fields"])


async def test_explicit_null_clears_a_nullable_column(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in(app_client, db_session, UserRole.PLAYER_PARENT)

    seeded = await app_client.patch("/me/profile", json={"school": "Lincoln High"})
    assert seeded.status_code == 200
    assert seeded.json()["role_detail"]["school"] == "Lincoln High"

    cleared = await app_client.patch("/me/profile", json={"school": None})
    assert cleared.status_code == 200
    assert cleared.json()["role_detail"]["school"] is None

    reread = await app_client.get("/me/profile")
    assert reread.json()["role_detail"]["school"] is None


async def test_omitted_key_leaves_the_column_unchanged(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in(app_client, db_session, UserRole.PLAYER_PARENT)

    seeded = await app_client.patch("/me/profile", json={"school": "Lincoln High"})
    assert seeded.status_code == 200

    unrelated_update = await app_client.patch(
        "/me/profile", json={"emergency_contact_name": "Jamie Guardian"}
    )
    assert unrelated_update.status_code == 200
    assert unrelated_update.json()["role_detail"]["school"] == "Lincoln High"


async def test_explicit_null_for_first_name_is_rejected_not_500(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in(app_client, db_session, UserRole.COACH)

    response = await app_client.patch("/me/profile", json={"first_name": None})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_failed"
    assert any(f["field"] == "first_name" for f in body["error"]["fields"])


async def test_player_parent_can_update_both_player_and_contact_fields(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in(app_client, db_session, UserRole.PLAYER_PARENT)

    response = await app_client.patch(
        "/me/profile",
        json={"school": "Lincoln High", "emergency_contact_name": "Jamie Guardian"},
    )

    assert response.status_code == 200
    detail = response.json()["role_detail"]
    assert detail["school"] == "Lincoln High"
    assert detail["emergency_contact_name"] == "Jamie Guardian"
