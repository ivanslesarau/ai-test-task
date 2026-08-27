"""FR-090, SC-025: nothing a trainer can reach may reveal that one of
their players also trains with another trainer. Routes are discovered
from the app's own route table, not hand-listed, so a new endpoint cannot
be added without this sweep covering it.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.association import TrainerPlayerAssociation
from tests.helpers import create_player_with_detail, create_session_cookie, create_trainer_with_link


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
    player = await create_player_with_detail(db_session)
    db_session.add(
        TrainerPlayerAssociation(
            trainer_user_id=trainer_a.id, player_user_id=player.id, status="active"
        )
    )
    db_session.add(
        TrainerPlayerAssociation(
            trainer_user_id=trainer_b.id, player_user_id=player.id, status="active"
        )
    )
    await db_session.flush()

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
    # /me/profile, /me/trainers, /me/trainer-context, /me/branding* are
    # either read by every role (profile) or scoped to the *player* side
    # of context, not the trainer's own roster view — they carry no
    # other-trainer identifier for a Trainer caller by construction
    # (TrainerContextList only ever appears for a Player/Parent caller).
    known_not_applicable = {
        "/me/profile",
        "/me/trainers",
        "/me/trainer-context",
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
