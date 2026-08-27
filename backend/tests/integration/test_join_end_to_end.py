"""quickstart.md US6 walk (T299): scenarios 6.4-6.6 and 6.12-6.13, which
the narrower unit-style tests in test_join_register.py, test_join_preview.py,
and test_trainer_roster.py don't chain together end to end. Written after
reconciling the quickstart table against the automated suite — these three
were genuine gaps, not scenarios covered elsewhere under a different name.
"""

import glob
from datetime import date, timedelta
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from tests.helpers import create_session_cookie, create_trainer_with_link

_TODAY = date.today()


def _outbox_messages_mentioning(outbox_dir: str, *needles: str) -> list[str]:
    """Synchronous by design (ASYNC230): a helper called from an async
    test, not blocking `open()`/`read_text()` lexically inside one."""
    matches = []
    for path in glob.glob(f"{outbox_dir}/*.txt"):
        content = Path(path).read_text(encoding="utf-8")
        if any(needle in content for needle in needles):
            matches.append(content)
    return matches


def _adult_payload(email: str) -> dict:
    return {
        "first_name": "Ann",
        "last_name": "Lee",
        "email": email,
        "password": "correct-horse-battery-987654",
        "phone": "+14155552671",
        "is_self": True,
        "player_name": None,
        "date_of_birth": (_TODAY - timedelta(days=366 * 25)).isoformat(),
        "gender": "prefer_not_to_say",
    }


async def test_6_4_through_6_6_full_registration_chain(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Register through a link, then — as that same signed-in session —
    confirm /me/trainers shows the link's trainer (6.4); sign in as the
    trainer and confirm the new player is on the roster (6.5); and
    confirm a confirmation email naming the trainer landed in the outbox
    (6.6)."""
    trainer, link = await create_trainer_with_link(db_session, business_name="Chain Academy")
    await db_session.commit()

    register = await app_client.post(
        f"/join/{link.code}/register", json=_adult_payload("chain@example.org")
    )
    assert register.status_code == 201

    # 6.4 — the same client still carries the session cookie the register
    # response set.
    trainers = await app_client.get("/me/trainers")
    assert trainers.status_code == 200
    body = trainers.json()
    assert len(body["trainers"]) == 1
    assert body["trainers"][0]["trainer_id"] == trainer.id
    assert body["active_trainer_id"] == trainer.id

    # 6.5 — sign in as the trainer and check the roster.
    trainer_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", trainer_token)

    roster = await app_client.get("/trainer/players")
    assert roster.status_code == 200
    names = {item["display_name"] for item in roster.json()["items"]}
    assert "Ann Lee" in names

    # 6.6 — a confirmation email naming the trainer is in the outbox.
    settings = get_settings()
    matches = _outbox_messages_mentioning(
        settings.email_outbox_dir, "chain@example.org", "Chain Academy"
    )
    assert any("Chain Academy" in m for m in matches), (
        "no outbox message names the trainer — FR-079's confirmation email is missing"
    )


async def test_6_12_and_6_13_regenerate_kills_old_code_but_keeps_associations(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    register = await app_client.post(
        f"/join/{link.code}/register", json=_adult_payload("survivor@example.org")
    )
    assert register.status_code == 201
    app_client.cookies.delete("pp_session")

    trainer_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", trainer_token)

    regenerate = await app_client.post("/me/share-link/regenerate")
    assert regenerate.status_code == 201
    app_client.cookies.delete("pp_session")

    # 6.12 — the old code is dead.
    old_preview = await app_client.get(f"/join/{link.code}")
    assert old_preview.status_code == 404
    assert old_preview.json()["error"]["code"] == "invitation_link_invalid"

    # 6.13 — the association the old code produced survives.
    trainer_token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", trainer_token)
    roster = await app_client.get("/trainer/players")
    names = {item["display_name"] for item in roster.json()["items"]}
    assert "Ann Lee" in names
