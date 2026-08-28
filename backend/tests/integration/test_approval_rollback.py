"""quickstart.md scenario 12.13 and 12.23 (US12, tasks.md T402, FR-151,
FR-142). An approval that cannot be completed leaves the request live,
not approved, and no association behind — and a financial kind is
refused outright, since no executor is registered for one."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import ApprovalRequest
from app.models.association import TrainerPlayerAssociation
from app.models.enums import ApprovalRequestKind
from app.repositories.share_link_repository import ShareLinkRepository
from tests.helpers import (
    create_approval_request,
    create_family,
    create_session_cookie,
    create_trainer_with_link,
)


async def test_approving_after_the_link_was_revoked_is_refused_and_changes_nothing(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    parent, profiles, _ = await create_family(db_session, children=1)
    trainer, link = await create_trainer_with_link(db_session, business_name="Revoked Academy")
    request = await create_approval_request(
        db_session,
        player_profile_id=profiles[0].id,
        parent_user_id=parent.id,
        trainer_user_id=trainer.id,
        share_link_id=link.id,
    )
    await db_session.commit()

    # Captured before the approval attempt below: a failed approval rolls
    # back the SAVEPOINT it opened, which expires every object this
    # session has loaded — a bare attribute access afterward would need
    # a synchronous reload AsyncSession cannot do (SQLAlchemy's
    # MissingGreenlet), so every id used past this point is a plain str.
    request_id, trainer_id, player_profile_id = request.id, trainer.id, profiles[0].id

    await ShareLinkRepository(db_session).revoke(link)
    await db_session.commit()

    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/me/approvals/{request_id}/approve")
    await db_session.commit()

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "approval_subject_unavailable"

    refreshed = await db_session.get(ApprovalRequest, request_id)
    assert refreshed is not None
    assert refreshed.status == "pending_parent_approval"

    association = (
        await db_session.execute(
            select(TrainerPlayerAssociation).where(
                TrainerPlayerAssociation.trainer_user_id == trainer_id,
                TrainerPlayerAssociation.player_profile_id == player_profile_id,
            )
        )
    ).scalar_one_or_none()
    assert association is None


async def test_approving_a_financial_request_is_refused_as_not_executable(
    app_client: AsyncClient, db_session: AsyncSession
) -> None:
    """FR-142, research.md R-46: the two financial kinds ship with no
    registered executor, so approving one is refused before any write is
    attempted."""
    parent, profiles, _ = await create_family(db_session, children=1)
    request = await create_approval_request(
        db_session,
        player_profile_id=profiles[0].id,
        parent_user_id=parent.id,
        kind=ApprovalRequestKind.TOKEN_SPEND,
        amount_minor=500,
        currency="USD",
    )
    await db_session.commit()

    token = await create_session_cookie(db_session, parent)
    await db_session.commit()
    app_client.cookies.set("pp_session", token)

    response = await app_client.post(f"/me/approvals/{request.id}/approve")
    await db_session.commit()

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "approval_kind_not_executable"

    refreshed = await db_session.get(ApprovalRequest, request.id)
    assert refreshed is not None
    assert refreshed.status == "pending_parent_approval"
