"""US1 (tasks.md T518): POST /trainer/coach-invitations and its list.

Covers a 201 with a seven-day expiry (FR-001, FR-002), the outbox email
carrying the trainer's name, the personal message, and the invitation URL
(FR-001, FR-003), and FR-008 — the response must be identical in shape and
status whether or not the invited address already holds an account.
"""

import glob
from datetime import datetime, timedelta
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import utcnow
from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_trainer_with_link, create_user


def _outbox_messages_mentioning(outbox_dir: str, *needles: str) -> list[str]:
    """Synchronous by design (ASYNC230): a helper called from an async
    test, not blocking `open()`/`read_text()` lexically inside one.

    Requires every needle in the same message — the outbox directory is
    shared across the whole test session (research.md's filesystem sink
    is not cleaned between tests), so an OR-match would also catch an
    unrelated message from a different test that happens to share one
    needle."""
    matches = []
    for path in glob.glob(f"{outbox_dir}/*.txt"):
        content = Path(path).read_text(encoding="utf-8")
        if all(needle in content for needle in needles):
            matches.append(content)
    return matches


async def _sign_in_trainer(
    db_session: AsyncSession,
    app_client: AsyncClient,
    *,
    business_name: str = "Elite Basketball Academy",
):
    trainer, _ = await create_trainer_with_link(db_session, business_name=business_name)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return trainer


async def test_issue_returns_201_with_a_seven_day_expiry_and_the_new_invitation(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)
    before = utcnow()

    response = await app_client.post(
        "/trainer/coach-invitations",
        json={
            "email": "Prospect@Example.ORG",
            "invitee_name": "Alex Prospect",
            "message": "We'd love to have you on our staff.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["invited_email"] == "prospect@example.org"  # lower-cased (data-model.md §101)
    assert body["invitee_name"] == "Alex Prospect"
    assert body["message"] == "We'd love to have you on our staff."
    assert body["state"] == "awaiting"
    assert body["accepted_at"] is None
    assert body["revoked_at"] is None
    assert body["blocked_reason"] is None
    assert body["coach"] is None

    issued_at = datetime.fromisoformat(body["issued_at"])
    expires_at = datetime.fromisoformat(body["expires_at"])
    delta = expires_at - issued_at
    assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1)
    assert issued_at >= before - timedelta(seconds=5)


async def test_issue_writes_an_outbox_email_carrying_the_trainer_name_message_and_url(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client, business_name="Chain Academy")

    response = await app_client.post(
        "/trainer/coach-invitations",
        json={
            "email": "future-coach@example.org",
            "invitee_name": None,
            "message": "Looking forward to working with you.",
        },
    )
    assert response.status_code == 201

    settings = get_settings()
    matches = _outbox_messages_mentioning(
        settings.email_outbox_dir, "future-coach@example.org", "Chain Academy"
    )
    assert len(matches) >= 1
    mail = matches[-1]
    assert "Chain Academy" in mail
    assert "Looking forward to working with you." in mail
    assert f"{settings.frontend_base_url}/coach-invite/" in mail


async def test_issue_response_is_identical_whether_or_not_the_address_already_has_an_account(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """FR-008: the trainer must never learn, from this response, whether
    the invited address already holds an account."""
    await _sign_in_trainer(db_session, app_client)
    existing = await create_user(
        db_session, role=UserRole.PLAYER_PARENT, email="already-has-account@example.org"
    )
    await db_session.commit()
    assert existing.email == "already-has-account@example.org"

    existing_response = await app_client.post(
        "/trainer/coach-invitations",
        json={"email": "already-has-account@example.org"},
    )
    new_response = await app_client.post(
        "/trainer/coach-invitations",
        json={"email": "brand-new-address@example.org"},
    )

    assert existing_response.status_code == 201
    assert new_response.status_code == 201
    assert sorted(existing_response.json().keys()) == sorted(new_response.json().keys())
    identical_fields = (
        "invitee_name",
        "message",
        "state",
        "accepted_at",
        "revoked_at",
        "blocked_reason",
        "coach",
    )
    for field in identical_fields:
        assert existing_response.json()[field] == new_response.json()[field]


async def test_issue_defaults_optional_fields_to_null_when_omitted(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_trainer(db_session, app_client)

    response = await app_client.post(
        "/trainer/coach-invitations", json={"email": "no-extras@example.org"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["invitee_name"] is None
    assert body["message"] is None
