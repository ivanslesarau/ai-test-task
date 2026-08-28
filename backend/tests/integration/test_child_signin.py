"""quickstart.md Story 11 scenarios 11.1-11.3 and 11.15-11.18 (US11,
tasks.md T379)."""

import glob
import re
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.base import new_uuid
from app.models.enums import UserRole
from tests.helpers import create_family, create_session_cookie, create_user


def _outbox_messages_mentioning(outbox_dir: str, *needles: str) -> list[str]:
    """Synchronous by design (ASYNC230): a helper called from an async
    test, not blocking `open()`/`read_text()` lexically inside one."""
    matches = []
    for path in glob.glob(f"{outbox_dir}/*.txt"):
        content = Path(path).read_text(encoding="utf-8")
        if all(needle in content for needle in needles):
            matches.append(content)
    return matches


def _extract_setup_token(content: str) -> str:
    match = re.search(r"token=(\S+)", content)
    assert match is not None, f"no setup token found in outbox message: {content}"
    return match.group(1)


async def _sign_in_parent(db_session: AsyncSession, app_client: AsyncClient):
    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return parent


# 11.1 -------------------------------------------------------------------


async def test_granting_with_a_fresh_email_sends_a_setup_link(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, _ = await create_family(db_session, children=1)
    await db_session.commit()
    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    child_profile = profiles[0]

    email = f"child-{new_uuid()}@example.org"
    response = await app_client.put(
        f"/me/players/{child_profile.id}/sign-in", json={"email": email}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["invitation_sent"] is True
    assert body["email"] == email
    assert body["player_profile_id"] == child_profile.id

    settings = get_settings()
    matches = _outbox_messages_mentioning(settings.email_outbox_dir, email)
    assert matches, "no setup-link email landed in the outbox for the new child account"
    assert "/set-password?token=" in matches[0]


# 11.2 -------------------------------------------------------------------


async def test_granting_with_the_parents_own_email_is_409(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, _ = await create_family(db_session, children=1)
    await db_session.commit()
    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.put(
        f"/me/players/{profiles[0].id}/sign-in", json={"email": parent.email}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_registered"


# 11.3 -------------------------------------------------------------------


async def test_the_setup_link_leads_to_a_working_child_session(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, _ = await create_family(db_session, children=2)
    await db_session.commit()
    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    child_profile = profiles[0]

    email = f"child-{new_uuid()}@example.org"
    grant = await app_client.put(f"/me/players/{child_profile.id}/sign-in", json={"email": email})
    assert grant.status_code == 201

    settings = get_settings()
    matches = _outbox_messages_mentioning(settings.email_outbox_dir, email)
    setup_token = _extract_setup_token(matches[0])

    app_client.cookies.delete("pp_session")
    setup = await app_client.post(
        "/auth/setup-password",
        json={"token": setup_token, "password": "childs-own-password-135"},
    )
    assert setup.status_code == 204

    sign_in = await app_client.post(
        "/auth/login", json={"email": email, "password": "childs-own-password-135"}
    )
    assert sign_in.status_code == 200
    assert sign_in.json()["is_child_account"] is True

    listed = await app_client.get("/me/players")
    assert listed.status_code == 200
    assert [p["id"] for p in listed.json()["profiles"]] == [child_profile.id]


# 11.15 ------------------------------------------------------------------


async def test_revoking_ends_the_session_but_leaves_the_profile_intact(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    await db_session.commit()
    child = child_accounts[0]
    child_token = await create_session_cookie(db_session, child)
    parent_token = await create_session_cookie(db_session, parent)
    await db_session.commit()

    app_client.cookies.set("pp_session", child_token)
    still_works = await app_client.get("/auth/session")
    assert still_works.status_code == 200

    app_client.cookies.set("pp_session", parent_token)
    revoke = await app_client.delete(f"/me/players/{profiles[0].id}/sign-in")
    assert revoke.status_code == 204

    app_client.cookies.set("pp_session", child_token)
    revoked = await app_client.get("/auth/session")
    assert revoked.status_code == 401

    app_client.cookies.set("pp_session", parent_token)
    still_listed = await app_client.get("/me/players")
    assert profiles[0].id in {p["id"] for p in still_listed.json()["profiles"]}


# 11.16 / 11.17 ------------------------------------------------------------


async def test_deactivating_and_reactivating_the_parent_suspends_and_restores_the_child(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    await db_session.commit()
    child = child_accounts[0]
    child_token = await create_session_cookie(db_session, child)
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    admin_token = await create_session_cookie(db_session, admin)
    await db_session.commit()

    app_client.cookies.set("pp_session", admin_token)
    deactivate = await app_client.post(f"/admin/users/{parent.id}/deactivate", json={"version": 1})
    assert deactivate.status_code == 200

    app_client.cookies.set("pp_session", child_token)
    blocked = await app_client.get("/auth/session")
    assert blocked.status_code == 401

    blocked_login = await app_client.post(
        "/auth/login", json={"email": child.email, "password": "correct-horse-battery-987654"}
    )
    assert blocked_login.status_code == 403

    app_client.cookies.set("pp_session", admin_token)
    reactivate = await app_client.post(f"/admin/users/{parent.id}/reactivate", json={"version": 2})
    assert reactivate.status_code == 200

    restored_login = await app_client.post(
        "/auth/login", json={"email": child.email, "password": "correct-horse-battery-987654"}
    )
    assert restored_login.status_code == 200


# 11.18 --------------------------------------------------------------------


async def test_removing_the_profile_ends_the_childs_sign_in(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    await db_session.commit()
    child = child_accounts[0]
    parent_token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", parent_token)

    response = await app_client.delete(f"/me/players/{profiles[0].id}")
    assert response.status_code == 204

    blocked_login = await app_client.post(
        "/auth/login", json={"email": child.email, "password": "correct-horse-battery-987654"}
    )
    assert blocked_login.status_code in (401, 403)
    assert blocked_login.json()["error"]["code"] in ("invalid_credentials", "account_not_active")


async def test_a_self_profiles_sign_in_is_refused(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    from tests.helpers import create_player_profile

    parent = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    self_profile = await create_player_profile(db_session, account=parent, kind="self")
    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.put(
        f"/me/players/{self_profile.id}/sign-in", json={"email": f"nope-{new_uuid()}@example.org"}
    )

    assert response.status_code == 422
