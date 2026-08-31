"""US2 (tasks.md T547): the per-origin lookup throttle a coach-invitation
preview reuses from the player join flow (research.md R2-05)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import create_coach_invitation, create_trainer_with_link


async def test_eleventh_unusable_lookup_from_one_origin_is_throttled(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    for _ in range(10):
        response = await app_client.get("/coach-invitations/not-a-real-token-value")
        assert response.status_code == 404

    throttled = await app_client.get("/coach-invitations/still-not-a-real-token")

    assert throttled.status_code == 429
    assert "Retry-After" in throttled.headers
    assert throttled.json()["error"]["code"] == "too_many_attempts"


async def test_a_usable_token_does_not_count_against_the_throttle(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    trainer, _ = await create_trainer_with_link(db_session)
    _invitation, raw_token = await create_coach_invitation(
        db_session, trainer=trainer, invited_email="repeat-preview@example.org"
    )
    await db_session.commit()

    for _ in range(20):
        response = await app_client.get(f"/coach-invitations/{raw_token}")
        assert response.status_code == 200
