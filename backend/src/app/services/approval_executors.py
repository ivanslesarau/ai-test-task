from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApprovalSubjectUnavailable
from app.db.base import utcnow
from app.models.approval import ApprovalRequest
from app.models.enums import AccountStatus, ApprovalRequestKind, AssociationStatus
from app.models.share_link import ShareLink
from app.repositories.association_repository import AssociationRepository
from app.repositories.share_link_repository import ShareLinkRepository
from app.repositories.user_repository import UserRepository

_SUBJECT_UNAVAILABLE_MESSAGE = (
    "That trainer is no longer available. The request is still waiting for you."
)


class ApprovalExecutor(Protocol):
    """One kind, one action (research.md R-42). `execute` runs inside the
    same transaction `approval_service.resolve` uses for the status flip
    to `approved` — a domain error it raises rolls both back through the
    SAVEPOINT the service opens, leaving the request in its previous live
    status rather than stuck "approved" with nothing carried out."""

    kind: ApprovalRequestKind

    async def execute(self, request: ApprovalRequest, *, db_session: AsyncSession) -> None: ...


class JoinTrainerExecutor:
    """Carries out an approved `join_trainer` request exactly as a parent
    adding a trainer directly would (FR-151) — reuses
    `AssociationRepository`'s check-then-insert convention and
    `ShareLinkRepository.is_usable`'s usability predicate rather than
    re-deriving either."""

    kind = ApprovalRequestKind.JOIN_TRAINER

    async def execute(self, request: ApprovalRequest, *, db_session: AsyncSession) -> None:
        users = UserRepository(db_session)
        associations = AssociationRepository(db_session)

        assert request.trainer_user_id is not None
        trainer = await users.get_by_id(request.trainer_user_id)
        if trainer is None or trainer.status_enum is not AccountStatus.ACTIVE:
            raise ApprovalSubjectUnavailable(_SUBJECT_UNAVAILABLE_MESSAGE)

        link: ShareLink | None = None
        if request.share_link_id is not None:
            link = await db_session.get(ShareLink, request.share_link_id)
            if link is None or not ShareLinkRepository.is_usable(link):
                raise ApprovalSubjectUnavailable(_SUBJECT_UNAVAILABLE_MESSAGE)

        existing = await associations.get(
            trainer_user_id=trainer.id, player_profile_id=request.player_profile_id
        )
        if existing is None:
            await associations.insert(
                trainer_user_id=trainer.id,
                player_profile_id=request.player_profile_id,
                share_link_id=request.share_link_id,
            )
            if link is not None:
                await ShareLinkRepository(db_session).increment_use_count(link)
        elif existing.status != AssociationStatus.ACTIVE.value:
            # A previously removed association is reactivated, the same
            # re-add path `FamilyService.add_trainer` uses (FR-127).
            existing.status = AssociationStatus.ACTIVE.value
            existing.updated_at = utcnow()
            if link is not None:
                await ShareLinkRepository(db_session).increment_use_count(link)
        # else: already active — idempotent no-op, exactly what
        # JoinService's own "already associated" branch does.


_REGISTRY: dict[ApprovalRequestKind, ApprovalExecutor] = {
    JoinTrainerExecutor.kind: JoinTrainerExecutor(),
}


def get_executor(kind: ApprovalRequestKind) -> ApprovalExecutor | None:
    """`None` for `usd_payment` and `token_spend` — deliberately
    unregistered (FR-142, research.md R-46). Epic-05 registers two more
    entries here and changes nothing in `approval_service.resolve`'s
    control flow."""
    return _REGISTRY.get(kind)
