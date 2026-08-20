from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus, UserRole
from tests.helpers import create_session_cookie, create_user


async def test_paging_search_filters_and_sort(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)

    await create_user(
        db_session,
        role=UserRole.TRAINER,
        email="alpha@example.org",
        first_name="Alpha",
        last_name="Trainer",
    )
    await create_user(
        db_session,
        role=UserRole.COACH,
        email="beta@example.org",
        first_name="Beta",
        last_name="Coach",
        status=AccountStatus.INACTIVE,
    )
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    all_page = await app_client.get("/admin/users", params={"page": 1, "page_size": 25})
    assert all_page.status_code == 200
    assert all_page.json()["total"] == 3  # admin + trainer + coach

    by_role = await app_client.get("/admin/users", params={"role": "trainer"})
    assert by_role.json()["total"] == 1
    assert by_role.json()["items"][0]["email"] == "alpha@example.org"

    by_status = await app_client.get("/admin/users", params={"status": "inactive"})
    assert by_status.json()["total"] == 1
    assert by_status.json()["items"][0]["email"] == "beta@example.org"

    by_search = await app_client.get("/admin/users", params={"q": "alpha"})
    assert by_search.json()["total"] == 1

    small_page = await app_client.get("/admin/users", params={"page": 1, "page_size": 1})
    assert len(small_page.json()["items"]) == 1
    assert small_page.json()["page_size"] == 1


async def test_page_size_is_capped_at_100(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.get("/admin/users", params={"page_size": 500})
    assert response.status_code == 422
