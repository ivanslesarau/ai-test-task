from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.models.association import TrainerPlayerAssociation
from app.models.enums import PlayerProfileKind
from app.models.player_profile import PlayerProfile
from app.models.role_details import TrainerOrganization
from app.models.user import User, UserProfile
from app.repositories.active_training_context_repository import ActiveTrainingContextRepository
from app.repositories.association_repository import AssociationRepository
from app.repositories.player_profile_repository import PlayerProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.branding import build_portal_branding_out
from app.schemas.training_context import TrainingContextEntry, TrainingContextList

_CandidateRow = tuple[TrainerPlayerAssociation, PlayerProfile, User, UserProfile]


class TrainingContextService:
    """Resolve-and-repair the active (player profile, trainer) pair
    (data-model.md §27, research.md R-36), list it for the switcher, and
    switch it. The only place a stored pair is trusted as read — every
    other caller goes through this service rather than reading
    `active_training_contexts` directly.

    Renamed from `TrainerContextService` (data-model.md §35): the context
    is now a pair, not a trainer alone, because FR-117 makes the
    isolation boundary a profile *and* a trainer together — a sibling on
    the same account is a different context from another sibling's, even
    with the same trainer.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self._users = UserRepository(db_session)
        self._profiles = PlayerProfileRepository(db_session)
        self._associations = AssociationRepository(db_session)
        self._contexts = ActiveTrainingContextRepository(db_session)

    async def _candidate_rows(self, viewer: User) -> list[_CandidateRow]:
        """Every pair this viewer may reach (FR-118, FR-119, research.md
        R-48). Scoping is read from `player_profiles.sign_in_user_id`
        rather than passed in by the caller: when a profile names this
        viewer as its child sign-in, the candidate set is that one
        profile alone; otherwise every live profile the viewer's account
        owns is offered, which is what a parent — and, until Phase C
        grants a child their own sign-in, every player_parent account —
        sees. No `player_profiles.sign_in_user_id` is ever set before
        Phase C ships, so every caller resolves parent-shaped today; the
        moment Phase C starts setting it, this method narrows to the
        single profile automatically, with no rewrite here (`require_parent`,
        added in Phase C, layers its own refusal on top rather than
        replacing this scoping)."""
        child_profile = await self._profiles.get_by_sign_in_user_id(viewer.id)
        if child_profile is not None:
            rows = await self._associations.list_active_for_player(child_profile.id)
            return [(a, child_profile, u, p) for a, u, p in rows]

        account_rows = await self._associations.list_active_for_account(viewer.id)
        return list(account_rows)

    async def is_child_account(self, viewer: User) -> bool:
        """`CurrentUser.is_child_account` (contract v1.2.0, research.md
        R-38): true exactly when a `player_profiles` row names this
        account as its child sign-in — derived, never stored twice.
        Shares `PlayerProfileRepository` with `_candidate_rows`, which is
        why this lives here rather than being queried directly from a
        router (Principle III)."""
        return (await self._profiles.get_by_sign_in_user_id(viewer.id)) is not None

    async def _display_name(self, profile: PlayerProfile) -> str:
        """The child's own name, or the account holder's name for a SELF
        profile — resolved server-side so the client never chooses
        between the two sources (research.md R-37)."""
        if profile.kind == PlayerProfileKind.CHILD.value:
            return f"{profile.first_name} {profile.last_name}"
        account_profile = await self._users.get_profile(profile.account_user_id)
        assert account_profile is not None
        return f"{account_profile.first_name} {account_profile.last_name}"

    async def resolve_active_context(self, viewer: User) -> tuple[str | None, str | None]:
        """A stored pair whose profile is no longer live, whose
        association is no longer Active, or whose trainer is no longer
        Active is replaced and the correction written back (FR-117,
        FR-120) — the same resolve-and-repair rule R-24 established,
        extended to a pair. Returns `(None, None)` only when the viewer
        holds no reachable Active association at all — a valid state,
        not an error."""
        rows = await self._candidate_rows(viewer)
        stored = await self._contexts.get_for_user(viewer.id)

        if not rows:
            if stored is not None and (
                stored.player_profile_id is not None or stored.trainer_user_id is not None
            ):
                await self._contexts.upsert(
                    user_id=viewer.id, player_profile_id=None, trainer_user_id=None
                )
            return None, None

        valid_pairs = {(a.player_profile_id, a.trainer_user_id) for a, _, _, _ in rows}
        current = (
            (stored.player_profile_id, stored.trainer_user_id)
            if stored is not None
            else (None, None)
        )
        if current in valid_pairs:
            return current

        fallback_association, fallback_profile, fallback_trainer, _ = rows[0]
        new_pair = (fallback_profile.id, fallback_trainer.id)
        await self._contexts.upsert(
            user_id=viewer.id, player_profile_id=new_pair[0], trainer_user_id=new_pair[1]
        )
        return new_pair

    async def list_for_account(self, viewer: User) -> TrainingContextList:
        active_player_profile_id, active_trainer_id = await self.resolve_active_context(viewer)
        rows = await self._candidate_rows(viewer)

        entries = []
        for association, profile, trainer_user, _trainer_profile in rows:
            trainer_org = await self._users.get_role_detail(trainer_user)
            business_name = (
                trainer_org.business_name if isinstance(trainer_org, TrainerOrganization) else ""
            )
            entries.append(
                TrainingContextEntry(
                    player_profile_id=profile.id,
                    player_display_name=await self._display_name(profile),
                    player_profile_kind=PlayerProfileKind(profile.kind),
                    trainer_id=trainer_user.id,
                    trainer_display_name=business_name,
                    branding=build_portal_branding_out(trainer_org),
                    joined_at=association.joined_at,
                )
            )

        return TrainingContextList(
            active_player_profile_id=active_player_profile_id,
            active_trainer_id=active_trainer_id,
            contexts=entries,
        )

    async def switch(
        self, viewer: User, *, player_profile_id: str, trainer_id: str
    ) -> TrainingContextList:
        """404, never 403, for a pair the caller holds no reachable
        Active association for — a role-style refusal would confirm the
        profile or the trainer exists, which is what FR-090 and FR-132
        both forbid (research.md R-48)."""
        rows = await self._candidate_rows(viewer)
        match = next(
            (row for row in rows if row[1].id == player_profile_id and row[2].id == trainer_id),
            None,
        )
        if match is None:
            raise NotFound("No such reachable training context.")

        await self._contexts.upsert(
            user_id=viewer.id, player_profile_id=player_profile_id, trainer_user_id=trainer_id
        )
        return await self.list_for_account(viewer)
