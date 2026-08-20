from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_directory_total_is_unchanged_and_erased_user_appears_as_deleted_user(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Stand-in for FR-046/FR-047/SC-009: this feature has no attendance
    or payment records yet (those belong to later epics), so the
    aggregate checked here is the directory's own count — erasure must
    not remove the row, only anonymize it, so the count is unchanged and
    the row is still present, now as "Deleted User"."""
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    coach = await create_user(db_session, role=UserRole.COACH, first_name="Cody", last_name="Coach")
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    before = await app_client.get("/admin/users")
    total_before = before.json()["total"]

    await app_client.post(f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "x"})

    after = await app_client.get("/admin/users")
    assert after.json()["total"] == total_before

    entries = {item["id"]: item for item in after.json()["items"]}
    assert entries[coach.id]["first_name"] == "Deleted"
    assert entries[coach.id]["last_name"] == "User"
    assert entries[coach.id]["status"] == "deleted"


async def test_search_for_the_former_name_or_email_finds_nothing(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    coach = await create_user(
        db_session,
        role=UserRole.COACH,
        email="findme@example.org",
        first_name="Findme",
        last_name="Coach",
    )
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    await app_client.post(f"/admin/users/{coach.id}/erase", json={"version": 1, "reason": "x"})

    by_old_name = await app_client.get("/admin/users", params={"q": "findme"})
    assert by_old_name.json()["total"] == 0
