"""US7 (tasks.md T646): `impersonation_sessions` is append-only by the
same defence-in-depth shape as `audit_entries` — the repository exposes
no update/delete beyond the one legitimate `close`, and the two SQLite
triggers (Alembic revision 0011, data-model.md §105) back that up:
direct DELETE and UPDATE are rejected, closing an *open* row succeeds,
and re-closing an already-closed row is rejected too (FR-055). The
original `audit_entries` triggers from revision 0004 must still hold.
"""

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def _sign_in_admin(app_client: AsyncClient, db_session: AsyncSession) -> object:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)
    return admin


async def test_deleting_an_impersonation_session_is_rejected_by_the_trigger(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    row_id = started.json()["id"]

    try:
        await db_session.execute(
            text("DELETE FROM impersonation_sessions WHERE id = :id"), {"id": row_id}
        )
        await db_session.commit()
        raised = False
    except IntegrityError:
        raised = True
        await db_session.rollback()

    assert raised, "DELETE against impersonation_sessions should have been rejected"


async def test_rewriting_a_closed_row_is_rejected_by_the_trigger(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    row_id = started.json()["id"]
    ended = await app_client.delete("/admin/impersonations/current")
    assert ended.status_code == 204

    try:
        await db_session.execute(
            text("UPDATE impersonation_sessions SET end_reason = 'tampered' WHERE id = :id"),
            {"id": row_id},
        )
        await db_session.commit()
        raised = False
    except IntegrityError:
        raised = True
        await db_session.rollback()

    assert raised, "Re-closing / rewriting an already-closed row should have been rejected"


async def test_rewriting_the_start_time_or_participants_of_an_open_row_is_rejected(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """The trigger's permitted shape is narrower than "any update to an
    open row" — it allows closing, not rewriting who or when (data-model.md
    §105)."""
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    row_id = started.json()["id"]

    try:
        await db_session.execute(
            text(
                "UPDATE impersonation_sessions SET started_at = '2020-01-01 00:00:00' "
                "WHERE id = :id"
            ),
            {"id": row_id},
        )
        await db_session.commit()
        raised = False
    except IntegrityError:
        raised = True
        await db_session.rollback()

    assert raised, "Rewriting started_at on an open row should have been rejected"


async def test_closing_an_open_row_through_the_service_succeeds(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """The one permitted mutation: the exit route's own conditional
    UPDATE (start -> end) goes through cleanly, proving the trigger is
    narrow, not blanket."""
    await _sign_in_admin(app_client, db_session)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()
    started = await app_client.post("/admin/impersonations", json={"user_id": trainer.id})
    assert started.status_code == 201

    ended = await app_client.delete("/admin/impersonations/current")

    assert ended.status_code == 204
    history = await app_client.get("/admin/impersonations")
    row = history.json()["items"][0]
    assert row["ended_at"] is not None
    assert row["end_reason"] == "exited"


async def test_audit_entries_original_triggers_still_hold(db_session: AsyncSession) -> None:
    """Revision 0011 touched `audit_entries` (adding `impersonator_user_id`)
    in the same migration as this feature's own triggers — confirm the
    two revision-0004 triggers on that unrelated table are unaffected
    (research.md R2-17)."""
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    await db_session.commit()
    await db_session.execute(
        text(
            "INSERT INTO audit_entries (id, actor_user_id, target_user_id, action, occurred_at) "
            "VALUES ('impersonation-append-only-guard', :actor, :actor, 'user_created', "
            "'2026-01-01 00:00:00')"
        ),
        {"actor": admin.id},
    )
    await db_session.commit()

    try:
        await db_session.execute(
            text("DELETE FROM audit_entries WHERE id = 'impersonation-append-only-guard'")
        )
        await db_session.commit()
        raised = False
    except IntegrityError:
        raised = True
        await db_session.rollback()

    assert raised, "audit_entries' own append-only trigger should still hold"


def test_impersonation_repository_exposes_no_mutation_beyond_close() -> None:
    """The primary control, checked directly — mirrors
    test_audit_append_only.py's equivalent assertion."""
    from app.repositories.impersonation_repository import ImpersonationRepository

    public_methods = {name for name in dir(ImpersonationRepository) if not name.startswith("_")}
    assert public_methods == {
        "insert",
        "close",
        "get_by_id",
        "get_open_for_admin",
        "get_open_for_target",
        "most_recent_ended_for_admin",
        "list_filtered",
    }
