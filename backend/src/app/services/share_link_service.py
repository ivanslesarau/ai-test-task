from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import InvitationLinkInvalid
from app.core.rate_limit import check_rate_limit
from app.core.security import generate_share_link_code
from app.models.enums import AccountStatus
from app.models.share_link import ShareLink
from app.models.user import User
from app.repositories.link_lookup_attempt_repository import LinkLookupAttemptRepository
from app.repositories.share_link_repository import ShareLinkRepository
from app.repositories.user_repository import UserRepository
from app.schemas.share_link import ShareLinkOut, build_share_link_out


class ShareLinkService:
    """Issue, read, regenerate a trainer's standing invitation link, plus
    the single five-part usability predicate every join path resolves
    through (research.md R-21, R-22, R-30)."""

    def __init__(self, db_session: AsyncSession, settings: Settings) -> None:
        self._settings = settings
        self._links = ShareLinkRepository(db_session)
        self._users = UserRepository(db_session)
        self._lookup_attempts = LinkLookupAttemptRepository(db_session)

    async def issue_standing_link(self, trainer_user_id: str) -> ShareLink:
        """Called by UserAdminService.create_user in the same transaction
        as trainer account creation (research.md R-22) — a lazy first-read
        creation would turn a GET into a write and take the SQLite write
        lock."""
        code = generate_share_link_code()
        return await self._links.insert_standing_link(
            trainer_user_id=trainer_user_id, created_by_user_id=trainer_user_id, code=code
        )

    async def get_current_for_trainer(self, trainer: User) -> ShareLinkOut:
        link = await self._links.get_current_for_trainer(trainer.id)
        if link is None:
            # Defensive only — every trainer receives a standing link at
            # creation time (research.md R-22) and the 0007 backfill
            # covers every trainer that predates the extension.
            link = await self.issue_standing_link(trainer.id)
        return build_share_link_out(link, frontend_base_url=self._settings.frontend_base_url)

    async def regenerate(self, trainer: User) -> ShareLinkOut:
        """Revokes the current code and issues a new one. The old row is
        retained — never deleted — because associations it already
        produced point at it (FR-069)."""
        current = await self._links.get_current_for_trainer(trainer.id)
        if current is not None:
            await self._links.revoke(current)
        new_link = await self.issue_standing_link(trainer.id)
        return build_share_link_out(new_link, frontend_base_url=self._settings.frontend_base_url)

    async def resolve_usable_link(self, code: str) -> tuple[ShareLink, User]:
        """The single refusal path for every reason a link can be unusable
        (FR-070) — unknown code, inactive, revoked, expired, exhausted, or
        an owning trainer that is not Active. One message, one exception,
        so the caller cannot learn which condition failed."""
        link = await self._links.get_by_code(code)
        if link is None or not ShareLinkRepository.is_usable(link):
            raise InvitationLinkInvalid("This link is no longer valid.")

        trainer = await self._users.get_by_id(link.trainer_user_id)
        if trainer is None or trainer.status_enum is not AccountStatus.ACTIVE:
            raise InvitationLinkInvalid("This link is no longer valid.")

        return link, trainer

    async def record_use(self, link: ShareLink) -> None:
        await self._links.increment_use_count(link)

    async def check_lookup_throttle(self, client_ip: str) -> None:
        """Per-origin only (FR-071) — an invalid code identifies nobody,
        so there is no second dimension to count, unlike sign-in's
        per-email-and-per-IP pair (R-06). Reuses the sign-in throttle's
        configured threshold and window, since FR-071 specifies the same
        10-per-15-minutes shape (research.md R-30)."""
        recent_failures = await self._lookup_attempts.count_recent_failures(
            client_ip=client_ip, window_minutes=self._settings.signin_window_minutes
        )
        check_rate_limit(
            recent_failure_count=recent_failures,
            max_attempts=self._settings.signin_max_attempts,
            window_minutes=self._settings.signin_window_minutes,
        )

    async def record_lookup_attempt(self, *, client_ip: str, successful: bool) -> None:
        await self._lookup_attempts.record(client_ip=client_ip, successful=successful)
