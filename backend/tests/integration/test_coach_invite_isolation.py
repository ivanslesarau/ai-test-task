"""US1 (tasks.md T520): another trainer's invitation is unreachable, a
non-Active trainer cannot issue or resend, and a Coach or Player/Parent is
refused on the request.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus, UserRole
from tests.helpers import create_session_cookie, create_trainer_with_link, create_user


async def test_another_trainers_invitation_is_absent_and_404s_on_resend_and_revoke(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, _ = await create_trainer_with_link(db_session, business_name="Owner Academy")
    owner_token = await create_session_cookie(db_session, owner)
    other, _ = await create_trainer_with_link(db_session, business_name="Other Academy")
    other_token = await create_session_cookie(db_session, other)
    await db_session.commit()

    app_client.cookies.set("pp_session", owner_token)
    issued = await app_client.post(
        "/trainer/coach-invitations", json={"email": "owned@example.org"}
    )
    assert issued.status_code == 201
    invitation_id = issued.json()["id"]

    app_client.cookies.set("pp_session", other_token)
    listing = await app_client.get("/trainer/coach-invitations")
    assert listing.status_code == 200
    assert invitation_id not in [item["id"] for item in listing.json()["items"]]

    resend = await app_client.post(f"/trainer/coach-invitations/{invitation_id}/resend")
    assert resend.status_code == 404

    revoke = await app_client.post(f"/trainer/coach-invitations/{invitation_id}/revoke")
    assert revoke.status_code == 404


async def test_a_non_active_trainer_cannot_issue_or_resend(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    issued = await app_client.post(
        "/trainer/coach-invitations", json={"email": "before-deactivation@example.org"}
    )
    assert issued.status_code == 201

    # Flipped directly on the row: `AuthService.authenticate_session`
    # re-checks status on every request regardless of how the session was
    # established, so this is refused at the authentication layer before
    # `CoachInvitationService`'s own defence-in-depth check would ever run
    # (both exist; only one is reachable through this HTTP path).
    trainer.status = AccountStatus.INACTIVE.value
    await db_session.flush()

    blocked_issue = await app_client.post(
        "/trainer/coach-invitations", json={"email": "after-deactivation@example.org"}
    )
    assert blocked_issue.status_code in (401, 403)

    blocked_resend = await app_client.post(
        f"/trainer/coach-invitations/{issued.json()['id']}/resend"
    )
    assert blocked_resend.status_code in (401, 403)


async def test_a_coach_or_player_parent_is_refused_on_every_route(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    coach = await create_user(db_session, role=UserRole.COACH)
    coach_token = await create_session_cookie(db_session, coach)
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    parent_token = await create_session_cookie(db_session, parent)
    await db_session.commit()

    for token in (coach_token, parent_token):
        app_client.cookies.set("pp_session", token)

        issue_response = await app_client.post(
            "/trainer/coach-invitations", json={"email": "nope@example.org"}
        )
        assert issue_response.status_code == 403

        list_response = await app_client.get("/trainer/coach-invitations")
        assert list_response.status_code == 403

        resend_response = await app_client.post("/trainer/coach-invitations/does-not-exist/resend")
        assert resend_response.status_code == 403

        revoke_response = await app_client.post("/trainer/coach-invitations/does-not-exist/revoke")
        assert revoke_response.status_code == 403
