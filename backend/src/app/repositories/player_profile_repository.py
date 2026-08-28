from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid, utcnow
from app.models.player_profile import PlayerProfile


class PlayerProfileRepository:
    """Queries only (data-model.md §26, §32, T321) — the near-duplicate
    *policy* (whether a match refuses the write, and the acknowledgement
    that overrides it) belongs to the service that calls
    `find_possible_duplicate`, not to this file (research.md R-45)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        account_user_id: str,
        kind: str,
        first_name: str | None,
        last_name: str | None,
        photo_key: str | None = None,
        date_of_birth: date | None,
        gender: str | None,
        school: str | None = None,
        jersey_number: str | None = None,
        skill_level: str | None = None,
        tokens_without_approval: bool = False,
        sign_in_user_id: str | None = None,
    ) -> PlayerProfile:
        """Raises sqlalchemy.exc.IntegrityError on a second SELF profile
        for the same account (`uq_player_profiles_one_self`) — the caller
        follows this codebase's check-then-insert convention rather than
        catching the race here."""
        now = utcnow()
        profile = PlayerProfile(
            id=new_uuid(),
            account_user_id=account_user_id,
            kind=kind,
            first_name=first_name,
            last_name=last_name,
            photo_key=photo_key,
            date_of_birth=date_of_birth,
            gender=gender,
            school=school,
            jersey_number=jersey_number,
            skill_level=skill_level,
            tokens_without_approval=tokens_without_approval,
            sign_in_user_id=sign_in_user_id,
            removed_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(profile)
        await self._session.flush()
        return profile

    async def get_by_id(self, profile_id: str) -> PlayerProfile | None:
        return await self._session.get(PlayerProfile, profile_id)

    async def list_all_for_account(self, account_user_id: str) -> list[PlayerProfile]:
        """Every profile the account holds, live or already soft-removed
        — erasure (data-model.md §30) clears identifying data from a
        removed profile too, since its history is still read on a
        trainer's roster."""
        result = await self._session.execute(
            select(PlayerProfile)
            .where(PlayerProfile.account_user_id == account_user_id)
            .order_by(PlayerProfile.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_live_for_account(self, account_user_id: str) -> list[PlayerProfile]:
        """The family list (data-model.md §26's `(account_user_id,
        removed_at)` index) — live profiles only, oldest first so a
        SELF profile (always created first, when present) sorts before
        the children added after it."""
        result = await self._session.execute(
            select(PlayerProfile)
            .where(
                PlayerProfile.account_user_id == account_user_id,
                PlayerProfile.removed_at.is_(None),
            )
            .order_by(PlayerProfile.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_self_for_account(self, account_user_id: str) -> PlayerProfile | None:
        """At most one row can match — `uq_player_profiles_one_self` makes
        it true by construction, not by this query."""
        result = await self._session.execute(
            select(PlayerProfile).where(
                PlayerProfile.account_user_id == account_user_id,
                PlayerProfile.kind == "self",
                PlayerProfile.removed_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_sign_in_user_id(self, sign_in_user_id: str) -> PlayerProfile | None:
        """The child's own reachable profile (research.md R-38, R-48) —
        the unique index on `sign_in_user_id` is what current-user
        resolution folds this lookup into."""
        result = await self._session.execute(
            select(PlayerProfile).where(PlayerProfile.sign_in_user_id == sign_in_user_id)
        )
        return result.scalar_one_or_none()

    async def list_signed_in_children(self, account_user_id: str) -> list[PlayerProfile]:
        """Every child sign-in this account has granted (research.md R-50)
        — the targets of the session-revocation cascade when the parent's
        own account leaves Active status. Filtered on `sign_in_user_id`
        alone rather than also on `removed_at`: T375 clears
        `sign_in_user_id` when a profile is removed, so a removed profile
        never matches here regardless."""
        result = await self._session.execute(
            select(PlayerProfile).where(
                PlayerProfile.account_user_id == account_user_id,
                PlayerProfile.sign_in_user_id.isnot(None),
            )
        )
        return list(result.scalars().all())

    async def find_possible_duplicate(
        self, *, account_user_id: str, first_name: str, last_name: str, date_of_birth: date
    ) -> list[PlayerProfile]:
        """Same account, same date of birth, case-insensitive match on the
        trimmed first and last name (research.md R-45) — deliberately
        narrow, so siblings named for the same relative on a different
        date do not collide. Excludes removed profiles: a re-added child
        is not a duplicate of their own soft-removed row."""
        result = await self._session.execute(
            select(PlayerProfile).where(
                PlayerProfile.account_user_id == account_user_id,
                PlayerProfile.removed_at.is_(None),
                PlayerProfile.date_of_birth == date_of_birth,
                func.lower(func.trim(PlayerProfile.first_name)) == first_name.strip().lower(),
                func.lower(func.trim(PlayerProfile.last_name)) == last_name.strip().lower(),
            )
        )
        return list(result.scalars().all())

    async def soft_remove(self, profile: PlayerProfile) -> None:
        """Soft removal (FR-111) — `removed_at` says when as well as
        whether. History elsewhere (associations, approval requests) is
        untouched; only this row stops being "live"."""
        profile.removed_at = utcnow()
        profile.updated_at = utcnow()
        await self._session.flush()
