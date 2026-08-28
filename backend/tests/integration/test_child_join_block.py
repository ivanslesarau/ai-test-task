"""quickstart.md Story 11 scenarios 11.11-11.14 (US11, tasks.md T382,
SC-030)."""

import glob
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.approval import ApprovalRequest
from app.models.enums import ApprovalRequestKind, ApprovalRequestStatus
from tests.helpers import (
    create_association,
    create_family,
    create_session_cookie,
    create_trainer_with_link,
)


def _outbox_messages_mentioning(outbox_dir: str, *needles: str) -> list[str]:
    """Synchronous by design (ASYNC230): a helper called from an async
    test, not blocking `open()`/`read_text()` lexically inside one."""
    matches = []
    for path in glob.glob(f"{outbox_dir}/*.txt"):
        content = Path(path).read_text(encoding="utf-8")
        if all(needle in content for needle in needles):
            matches.append(content)
    return matches


async def _live_requests_for_profile(
    db_session: AsyncSession, player_profile_id: str
) -> list[ApprovalRequest]:
    result = await db_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.player_profile_id == player_profile_id)
    )
    return list(result.scalars().all())


# 11.11 / 11.12 / 11.13 ------------------------------------------------------


async def test_a_child_following_a_new_trainers_link_is_blocked_once_and_notified_once(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    trainer, link = await create_trainer_with_link(db_session, business_name="Brand New Academy")
    await db_session.commit()

    child = child_accounts[0]
    child_profile = profiles[0]
    token = await create_session_cookie(db_session, child)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    # 11.11 — committed immediately afterward, mirroring the real
    # per-request commit boundary db/session.py's get_db_session gives
    # every production request (app_client's fixture overrides that
    # dependency with one shared session across the whole test).
    first = await app_client.post(f"/join/{link.code}/accept")
    await db_session.commit()
    assert first.status_code == 403
    assert first.json()["error"]["code"] == "child_must_ask_parent"

    # No association was created, and exactly one live request exists.
    live_requests = await _live_requests_for_profile(db_session, child_profile.id)
    assert len(live_requests) == 1
    request = live_requests[0]
    assert request.kind == ApprovalRequestKind.JOIN_TRAINER.value
    assert request.trainer_user_id == trainer.id
    assert request.parent_user_id == parent.id
    assert request.status == ApprovalRequestStatus.PENDING_PARENT_APPROVAL.value

    # 11.12 — exactly one email, to the parent, naming the child and the trainer.
    settings = get_settings()
    matches = _outbox_messages_mentioning(
        settings.email_outbox_dir, parent.email, "Brand New Academy"
    )
    assert len(matches) == 1
    assert "Brand New Academy" in matches[0]

    # 11.13 — repeat three more times: still no association, no further email.
    for _ in range(3):
        repeat = await app_client.post(f"/join/{link.code}/accept")
        await db_session.commit()
        assert repeat.status_code == 403
        assert repeat.json()["error"]["code"] == "child_must_ask_parent"

    live_after_repeats = await _live_requests_for_profile(db_session, child_profile.id)
    assert len(live_after_repeats) == 1

    matches_after_repeats = _outbox_messages_mentioning(
        settings.email_outbox_dir, parent.email, "Brand New Academy"
    )
    assert len(matches_after_repeats) == 1, "a repeat ask must not send a second email (R-51)"


# 11.14 -----------------------------------------------------------------------


async def test_a_child_following_the_link_of_a_trainer_they_already_train_with_is_told_so(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    trainer, link = await create_trainer_with_link(db_session, business_name="Already Trained")
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profiles[0].id)
    await db_session.commit()

    token = await create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/join/{link.code}/accept")

    assert response.status_code == 200
    body = response.json()
    assert body["already_associated_profile_ids"] == [profiles[0].id]

    live_requests = await _live_requests_for_profile(db_session, profiles[0].id)
    assert live_requests == []

    settings = get_settings()
    matches = _outbox_messages_mentioning(
        settings.email_outbox_dir, parent.email, "Already Trained"
    )
    assert matches == []
