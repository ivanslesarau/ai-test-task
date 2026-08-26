from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from tests.helpers import create_session_cookie, create_user


async def test_creating_a_user_writes_created_and_invited_audit_entries(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await create_user(db_session, role=UserRole.SUPER_ADMIN)
    token = await create_session_cookie(db_session, admin)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    created = await app_client.post(
        "/admin/users",
        json={
            "role": "coach",
            "email": "audited-coach@example.org",
            "first_name": "Aud",
            "last_name": "Ited",
            "phone": "+14155552671",
        },
    )
    assert created.status_code == 201
    new_user_id = created.json()["user"]["id"]

    audit = await app_client.get(f"/admin/users/{new_user_id}/audit")
    assert audit.status_code == 200
    actions = [e["action"] for e in audit.json()["items"]]
    assert "user_created" in actions
    assert "invitation_issued" in actions

    created_entry = next(e for e in audit.json()["items"] if e["action"] == "user_created")
    assert created_entry["actor"]["id"] == admin.id
    assert "audited-coach@example.org" in created_entry["detail"]
