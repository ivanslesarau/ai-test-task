"""Feature 002 extension of test_no_internal_leakage.py (FR-056/SC-012,
tasks.md T656): the shared exception-handling machinery is already
proven generic there; this file's own job is narrower — confirming that
none of this feature's *own* routers bypass it and leak a raw coach
invitation token, a session token, or an internal detail through one of
their own error paths.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.enums import UserRole
from tests.helpers import (
    create_coach,
    create_coach_invitation,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)

_FORBIDDEN_SUBSTRINGS = [
    "Traceback",
    "sqlite3",
    "sqlalchemy",
    "IntegrityError",
    "password_hash",
    "token_hash",
    '.py", line',
]


def _assert_body_is_clean(text: str, *, secrets: list[str] | None = None) -> None:
    lowered = text.lower()
    for marker in _FORBIDDEN_SUBSTRINGS:
        assert marker.lower() not in lowered, f"response leaked internal detail: {marker!r}"
    for secret in secrets or []:
        assert secret not in text, f"response leaked a raw secret: {secret!r}"


async def _sign_in(app_client: AsyncClient, db_session: AsyncSession, user: object) -> None:
    token = await create_session_cookie(db_session, user)  # type: ignore[arg-type]
    await db_session.commit()
    app_client.cookies.set("pp_session", token)


async def test_an_invalid_coach_invitation_token_leaks_nothing(app_client: AsyncClient) -> None:
    guessed_token = "not-a-real-token-abcdefghijklmnopqrstuvwxyz"

    response = await app_client.get(f"/coach-invitations/{guessed_token}")

    assert response.status_code == 404
    _assert_body_is_clean(response.text, secrets=[guessed_token])


async def test_a_coach_already_assigned_refusal_leaks_no_trainer_identity(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """SC-003 as a raw-text leakage check, on top of the field-level
    non-disclosure `test_coach_one_trainer.py` already proves: neither
    trainer's business name may appear anywhere in the response text,
    including inside any incidentally-echoed detail."""
    trainer_a, _ = await create_trainer_with_link(db_session, business_name="Trainer A Academy")
    trainer_b, _ = await create_trainer_with_link(
        db_session, business_name="Trainer B Sporting Club"
    )
    coach = await create_coach(
        db_session, email="employed@example.org", trainer_user_id=trainer_b.id, joined_at=utcnow()
    )
    _invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer_a, invited_email="employed@example.org"
    )
    await _sign_in(app_client, db_session, coach)

    response = await app_client.post(f"/coach-invitations/{raw_token}/accept")

    assert response.status_code == 409
    _assert_body_is_clean(
        response.text,
        secrets=["Trainer A Academy", "Trainer B Sporting Club", raw_token],
    )


async def test_an_availability_validation_refusal_leaks_no_internal_detail(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    coach = await create_user(db_session, role=UserRole.COACH)
    from app.models.role_details import CoachDetail

    db_session.add(CoachDetail(user_id=coach.id, is_publicly_visible=False))
    await db_session.flush()
    await _sign_in(app_client, db_session, coach)

    response = await app_client.put(
        "/me/availability",
        json={"slots": [{"day_of_week": 0, "start_minute": 600, "end_minute": 500}]},
    )

    assert response.status_code == 422
    _assert_body_is_clean(response.text)


async def test_an_impersonation_refusal_leaks_no_internal_detail(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    await _sign_in(app_client, db_session, admin)

    response = await app_client.post("/admin/impersonations", json={"user_id": admin.id})

    assert response.status_code == 422
    _assert_body_is_clean(response.text)


async def test_the_impersonation_history_leaks_no_session_token(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await _sign_in(app_client, db_session, admin)

    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201
    raw_cookie = app_client.cookies.get("pp_session")
    ended = await app_client.delete("/admin/impersonations/current")
    assert ended.status_code == 204

    history = await app_client.get("/admin/impersonations")

    assert history.status_code == 200
    _assert_body_is_clean(history.text, secrets=[raw_cookie] if raw_cookie else [])
