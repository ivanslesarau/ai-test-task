"""Every action FR-132 forbids a signed-in child, submitted **directly**
rather than through the interface (US11, tasks.md T380). This is SC-029.

Payment methods, purchasing tokens, and completing a purchase without
approval have no endpoint yet in this codebase — they belong to Epic-05
(see `app.core.errors.ApprovalKindNotExecutable`'s own docstring) — so
there is nothing to submit directly against for those three items; this
file's job is to prove every item FR-132 forbids that **does** have a
reachable route today is refused, and to record the ones that don't as a
documented gap rather than a silent omission.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import (
    create_association,
    create_family,
    create_session_cookie,
    create_trainer_with_link,
)


async def _sign_in_a_child(db_session: AsyncSession, app_client: AsyncClient):
    parent, profiles, child_accounts = await create_family(
        db_session, children=2, with_sign_in=True
    )
    token = await create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return parent, profiles, child_accounts


# FR-132: "owning a child profile of their own" -----------------------------


async def test_a_child_cannot_own_a_child_profile(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_a_child(db_session, app_client)

    response = await app_client.post(
        "/me/players",
        json={
            "first_name": "Probe",
            "last_name": "Child",
            "date_of_birth": "2015-01-01",
            "gender": "male",
        },
    )

    assert response.status_code == 403


# FR-132: "changing any trainer association" ---------------------------------


async def test_a_child_cannot_add_a_trainer_association(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, profiles, _ = await _sign_in_a_child(db_session, app_client)

    response = await app_client.post(
        f"/me/players/{profiles[0].id}/trainers", json={"trainer_id": "nonexistent"}
    )

    assert response.status_code == 403


async def test_a_child_cannot_remove_a_trainer_association(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts = await create_family(
        db_session, children=1, with_sign_in=True
    )
    trainer, _ = await create_trainer_with_link(db_session)
    association = await create_association(
        db_session, trainer_id=trainer.id, player_profile_id=profiles[0].id
    )
    token = await create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.delete(f"/me/players/{profiles[0].id}/trainers/{association.id}")

    assert response.status_code == 403


async def test_a_child_cannot_join_a_new_trainer(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """FR-132's "joining a new trainer" — routed to `child_must_ask_parent`
    rather than a bare 403 (FR-137); the fuller walk lives in
    test_child_join_block.py, this is the direct-submission check."""
    _, _, child_accounts = await _sign_in_a_child(db_session, app_client)
    trainer, link = await create_trainer_with_link(db_session)
    await db_session.commit()

    response = await app_client.post(f"/join/{link.code}/accept")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "child_must_ask_parent"


# FR-132: "deleting their own account" ---------------------------------------


async def test_a_child_cannot_delete_their_own_account() -> None:
    """No self-service account deletion exists anywhere in this codebase
    today — only Super-Admin erasure (`POST /admin/users/{id}/erase`,
    itself Super-Admin-only per the permission matrix). There is nothing
    for a child to submit directly against; recorded here so the gap is
    documented rather than silently assumed."""


# FR-132: "reading or changing anything belonging to the parent or to a
# sibling" --------------------------------------------------------------


async def test_a_child_cannot_read_a_siblings_profile(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, profiles, _ = await _sign_in_a_child(db_session, app_client)

    response = await app_client.get(f"/me/players/{profiles[1].id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] != "forbidden"


async def test_a_child_cannot_change_a_siblings_profile(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, profiles, _ = await _sign_in_a_child(db_session, app_client)

    response = await app_client.patch(
        f"/me/players/{profiles[1].id}", json={"school": "Sibling's School"}
    )

    assert response.status_code == 404


async def test_a_child_cannot_remove_a_siblings_profile(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """403, not 404, here: removal is refused for a child unconditionally
    (they may not remove even their own profile), so `RequireParentDep`
    refuses before reachability is ever checked — unlike the read/PATCH
    routes above, which distinguish "your own" from "a sibling's" and so
    give 404 for the latter (R-48)."""
    _, profiles, _ = await _sign_in_a_child(db_session, app_client)

    response = await app_client.delete(f"/me/players/{profiles[1].id}")

    assert response.status_code == 403


async def test_a_child_cannot_grant_or_revoke_a_siblings_sign_in(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, profiles, _ = await _sign_in_a_child(db_session, app_client)

    grant = await app_client.put(
        f"/me/players/{profiles[1].id}/sign-in", json={"email": "sibling-probe@example.org"}
    )
    assert grant.status_code == 403

    revoke = await app_client.delete(f"/me/players/{profiles[1].id}/sign-in")
    assert revoke.status_code == 403


async def test_a_child_naming_a_siblings_profile_as_training_context_gets_404(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, child_accounts = await create_family(
        db_session, children=2, with_sign_in=True
    )
    trainer, _ = await create_trainer_with_link(db_session)
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=profiles[1].id)
    token = await create_session_cookie(db_session, child_accounts[0])
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.put(
        "/me/context",
        json={"player_profile_id": profiles[1].id, "trainer_id": trainer.id},
    )

    assert response.status_code == 404


# FR-132: "changing any setting the parent owns — including the setting
# that governs their own token spending" -------------------------------


async def test_a_child_cannot_widen_their_own_tokens_without_approval(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, profiles, _ = await _sign_in_a_child(db_session, app_client)

    response = await app_client.patch(
        f"/me/players/{profiles[0].id}", json={"tokens_without_approval": True}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "parent_only_field"


async def test_a_child_cannot_grant_themself_a_sign_in(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A child has no profile of their own to name (FR-132's "owning a
    child profile" already refuses that), so this targets their own
    reachable profile — still refused, since granting a sign-in is a
    setting the parent owns."""
    _, profiles, _ = await _sign_in_a_child(db_session, app_client)

    response = await app_client.put(
        f"/me/players/{profiles[0].id}/sign-in", json={"email": "self-probe@example.org"}
    )

    assert response.status_code == 403
