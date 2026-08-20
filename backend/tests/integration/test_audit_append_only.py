"""FR-055: no one can alter or remove an audit entry through the
platform. The repository having no update/delete method is the primary
control; these SQLite triggers (Alembic revision 0004) are defence in
depth, verified here by attempting the raw SQL the repository would
never issue."""

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_user


async def test_updating_an_audit_entry_is_rejected_by_the_trigger(
    db_session: AsyncSession,
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    await db_session.commit()

    await db_session.execute(
        text(
            "INSERT INTO audit_entries (id, actor_user_id, target_user_id, action, occurred_at) "
            "VALUES ('audit-append-only-1', :actor, :actor, 'user_created', '2026-01-01 00:00:00')"
        ),
        {"actor": admin.id},
    )
    await db_session.commit()

    try:
        await db_session.execute(
            text("UPDATE audit_entries SET action = 'tampered' WHERE id = 'audit-append-only-1'")
        )
        await db_session.commit()
        raised = False
    except IntegrityError:
        raised = True
        await db_session.rollback()

    assert raised, "UPDATE against audit_entries should have been rejected by the trigger"


async def test_deleting_an_audit_entry_is_rejected_by_the_trigger(
    db_session: AsyncSession,
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    await db_session.commit()

    await db_session.execute(
        text(
            "INSERT INTO audit_entries (id, actor_user_id, target_user_id, action, occurred_at) "
            "VALUES ('audit-append-only-2', :actor, :actor, 'user_created', '2026-01-01 00:00:00')"
        ),
        {"actor": admin.id},
    )
    await db_session.commit()

    try:
        await db_session.execute(text("DELETE FROM audit_entries WHERE id = 'audit-append-only-2'"))
        await db_session.commit()
        raised = False
    except IntegrityError:
        raised = True
        await db_session.rollback()

    assert raised, "DELETE against audit_entries should have been rejected by the trigger"


def test_audit_repository_exposes_no_mutation_method() -> None:
    """The primary control, checked directly: AuditRepository must never
    grow an update/delete method, regardless of what the triggers do."""
    from app.repositories.audit_repository import AuditRepository

    public_methods = {name for name in dir(AuditRepository) if not name.startswith("_")}
    assert public_methods == {"add", "list_for_target"}
