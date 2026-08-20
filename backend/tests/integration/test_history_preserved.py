from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_deactivated_user_still_appears_in_the_directory_marked_inactive(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    await app_client.post(f"/admin/users/{trainer.id}/deactivate", json={"version": 1})

    directory = await app_client.get("/admin/users")
    entries = {item["id"]: item for item in directory.json()["items"]}

    assert trainer.id in entries
    assert entries[trainer.id]["status"] == "inactive"


async def test_directory_totals_are_unchanged_by_deactivation(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A stand-in for FR-039/SC-008: this feature has no attendance or
    payment records yet (those belong to later epics), so the aggregate
    checked here is the directory's own participant count — deactivating
    an account must not remove it from that count, only change its
    status column."""
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    trainer = await create_user(db_session, role=UserRole.TRAINER)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    before = await app_client.get("/admin/users")
    total_before = before.json()["total"]

    await app_client.post(f"/admin/users/{trainer.id}/deactivate", json={"version": 1})

    after = await app_client.get("/admin/users")
    assert after.json()["total"] == total_before
