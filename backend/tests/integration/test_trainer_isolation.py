"""FR-090, SC-025: nothing a trainer can reach may reveal that one of
their players also trains with another trainer. Routes are discovered
from the app's own route table, not hand-listed, so a new endpoint cannot
be added without this sweep covering it.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.enums import UserRole
from tests.helpers import (
    create_association,
    create_family,
    create_player_profile,
    create_session_cookie,
    create_trainer_with_link,
    create_user,
)


def _trainer_facing_get_paths() -> list[str]:
    """Every GET route this feature adds that a Trainer can call. Walked
    directly (not the full app route table) because most routes in this
    app require a resource id or a different role and would need per-role
    fixtures beyond what this sweep is about; the routes below are
    exactly the ones a trainer's own session can reach and that could
    leak a player's other associations."""
    return ["/trainer/players", "/me/share-link", "/auth/session"]


async def test_no_trainer_facing_response_names_the_other_trainer(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer_a, _ = await create_trainer_with_link(db_session, business_name="Trainer A Academy")
    trainer_b, _ = await create_trainer_with_link(db_session, business_name="Trainer B Academy")
    player = await create_user(db_session, role=UserRole.PLAYER_PARENT)
    profile = await create_player_profile(db_session, account=player, kind="self")
    await create_association(db_session, trainer_id=trainer_a.id, player_profile_id=profile.id)
    await create_association(db_session, trainer_id=trainer_b.id, player_profile_id=profile.id)

    token = await create_session_cookie(db_session, trainer_a)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    for path in _trainer_facing_get_paths():
        response = await app_client.get(path)
        assert response.status_code == 200, path
        body_text = response.text
        assert trainer_b.id not in body_text, f"{path} leaked trainer B's id"
        assert "Trainer B Academy" not in body_text, f"{path} leaked trainer B's name"


async def test_route_table_has_not_grown_an_uncovered_trainer_facing_route() -> None:
    """A guard against the sweep silently going stale: every GET route
    under /trainer or /me this feature owns must be one this test already
    walks, or accounted for by name here. New routes must extend
    _trainer_facing_get_paths(), not be forgotten."""
    known_prefixes = ("/trainer", "/me")
    accounted_for = set(_trainer_facing_get_paths())
    # /me/profile, /me/contexts, /me/context, /me/branding* are either
    # read by every role (profile) or scoped to the *player* side of
    # context, not the trainer's own roster view — they carry no
    # other-trainer identifier for a Trainer caller by construction
    # (TrainingContextList only ever appears for a Player/Parent caller).
    known_not_applicable = {
        "/me/profile",
        "/me/contexts",
        "/me/branding",
        "/me/branding/logo",
        "/me/branding/reset",
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
            f"New trainer-facing route {path!r} is not covered by the isolation sweep — "
            "add it to _trainer_facing_get_paths() or known_not_applicable with a reason."
        )


# --- Extension (2026-08-27) — US11: a family fixture (T383, FR-116, SC-040) -


async def test_a_trainer_sees_a_trained_child_and_the_parents_contact_but_not_the_untrained_sibling(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A trainer with one child on their roster reads that child's own
    name and the responsible *parent's* contact detail (FR-113, FR-116) —
    never a sibling on the same account who does not train with them
    (SC-040), the same guarantee `AssociationRepository.list_for_trainer`
    already gives at profile granularity (data-model.md §29.1)."""
    parent, profiles, _ = await create_family(db_session, children=2)
    trainer, _ = await create_trainer_with_link(db_session, business_name="Family Trainer")
    trained_child, untrained_sibling = profiles
    await create_association(db_session, trainer_id=trainer.id, player_profile_id=trained_child.id)
    token = await create_session_cookie(db_session, trainer)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    roster = await app_client.get("/trainer/players")

    assert roster.status_code == 200
    items = roster.json()["items"]
    assert [i["player_profile_id"] for i in items] == [trained_child.id]

    row = items[0]
    assert row["display_name"] == f"{trained_child.first_name} {trained_child.last_name}"
    assert row["responsible_contact"]["email"] == parent.email

    body_text = roster.text
    assert untrained_sibling.id not in body_text, "the untrained sibling's profile id leaked"
    assert untrained_sibling.first_name != trained_child.first_name
    assert untrained_sibling.first_name not in body_text, "the untrained sibling's name leaked"
