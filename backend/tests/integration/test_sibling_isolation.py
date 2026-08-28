"""Sibling isolation, swept across every context-scoped route a signed-in
child can reach (US11, tasks.md T381). This is SC-028 and SC-040.

A different failure from `test_child_permissions.py`'s matrix: that file
proves an action is *refused*; this one proves that wherever a child *is*
let in, no response body ever carries a sibling's data, and that naming a
sibling's profile is a 404, never a 403 (research.md R-48) — a
distinguishing refusal would itself confirm the sibling's profile exists.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from tests.helpers import (
    create_association,
    create_family,
    create_session_cookie,
    create_trainer_with_link,
)


async def _two_child_family(db_session: AsyncSession):
    """Both children signed in, each trained by a distinct trainer, so a
    leak of the sibling's association would be visible either as a second
    profile id or as the other trainer's business name."""
    parent, profiles, child_accounts = await create_family(
        db_session, children=2, with_sign_in=True
    )
    trainer_a, _ = await create_trainer_with_link(db_session, business_name="Sibling A Academy")
    trainer_b, _ = await create_trainer_with_link(db_session, business_name="Sibling B Academy")
    await create_association(db_session, trainer_id=trainer_a.id, player_profile_id=profiles[0].id)
    await create_association(db_session, trainer_id=trainer_b.id, player_profile_id=profiles[1].id)
    return parent, profiles, child_accounts, trainer_a, trainer_b


def _child_facing_get_paths() -> list[str]:
    """Every GET route a signed-in child's own session can reach that
    could conceivably echo back a sibling's identity."""
    return ["/me/players", "/auth/session", "/me/contexts"]


async def test_no_child_facing_response_names_the_sibling(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts, trainer_a, trainer_b = await _two_child_family(db_session)
    token = await create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    sibling_profile = profiles[1]

    for path in _child_facing_get_paths():
        response = await app_client.get(path)
        assert response.status_code == 200, path
        body_text = response.text
        assert sibling_profile.id not in body_text, f"{path} leaked the sibling's profile id"
        assert "Sibling B Academy" not in body_text, f"{path} leaked the sibling's trainer"
        assert child_accounts[1].email not in body_text, f"{path} leaked the sibling's email"

    own = await app_client.get(f"/me/players/{profiles[0].id}")
    assert own.status_code == 200
    assert sibling_profile.id not in own.text


async def test_a_childs_own_profile_list_holds_exactly_one_entry(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, profiles, child_accounts, _, _ = await _two_child_family(db_session)
    token = await create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    listed = await app_client.get("/me/players")
    assert listed.status_code == 200
    assert [p["id"] for p in listed.json()["profiles"]] == [profiles[0].id]


async def test_naming_a_siblings_profile_is_404_not_403_everywhere_reachable(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts, trainer_a, trainer_b = await _two_child_family(db_session)
    token = await create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    sibling_profile = profiles[1]

    read = await app_client.get(f"/me/players/{sibling_profile.id}")
    assert read.status_code == 404
    assert read.json()["error"]["code"] != "forbidden"

    switch = await app_client.put(
        "/me/context",
        json={"player_profile_id": sibling_profile.id, "trainer_id": trainer_b.id},
    )
    assert switch.status_code == 404
    assert switch.json()["error"]["code"] != "forbidden"

    photo = await app_client.put(
        f"/me/players/{sibling_profile.id}/photo",
        files={"file": ("photo.png", b"not-a-real-image", "image/png")},
    )
    assert photo.status_code == 404
    assert photo.json()["error"]["code"] != "forbidden"


def test_route_table_has_not_grown_an_uncovered_child_facing_route() -> None:
    """A guard against the sweep going stale, mirroring
    test_trainer_isolation.py's own guard: every GET route under /me this
    feature owns must be walked above or accounted for by name here."""
    known_prefixes = ("/me",)
    accounted_for = set(_child_facing_get_paths()) | {"/me/players/{profile_id}"}
    known_not_applicable = {
        "/me/profile",
        "/me/branding",
        "/me/branding/logo",
        "/me/branding/reset",
        "/me/share-link",
    }

    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if path is None or "GET" not in methods:
            continue
        if not path.startswith(known_prefixes):
            continue
        if path in accounted_for or path in known_not_applicable:
            continue
        raise AssertionError(
            f"New /me-facing route {path!r} is not covered by the sibling isolation sweep — "
            "add it to _child_facing_get_paths() or known_not_applicable with a reason."
        )
