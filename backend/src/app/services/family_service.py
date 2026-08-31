from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import (
    NotFound,
    ParentOnlyField,
    PayloadTooLarge,
    PermissionDenied,
    PlayerProfileNotFound,
    PossibleDuplicateProfile,
    UnsupportedMediaType,
    ValidationFailure,
)
from app.core.family_rules import age_on, is_valid_age_for_kind, self_profile_rejects_names
from app.db.base import new_uuid, utcnow
from app.models.enums import AccountStatus, AssociationStatus, PlayerProfileKind
from app.models.player_profile import PlayerProfile as PlayerProfileModel
from app.models.role_details import TrainerOrganization
from app.models.user import User
from app.repositories.association_repository import AssociationRepository
from app.repositories.availability_repository import AvailabilityRepository
from app.repositories.player_profile_repository import PlayerProfileRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.player_profile import (
    AddPlayerTrainerRequest,
    CreateChildProfileRequest,
    PlayerProfileAssociation,
    PlayerProfileList,
)
from app.schemas.player_profile import (
    PlayerProfile as PlayerProfileOut,
)
from app.schemas.profile import PhotoUrls
from app.services.image_processing import (
    UnsupportedImageError,
    decode_and_validate,
    encode,
    make_thumbnail,
)
from app.services.ports.photo_storage import PhotoStorage, thumbnail_key_for
from app.services.share_link_service import ShareLinkService


class FamilyService:
    """`/me/players` — a family's own player profiles and, per profile,
    the trainers it trains with (US9, US10; data-model.md §26, §29.1).

    Ownership and reachability are validated here, never in the router
    (constitution Principle III). Every method resolves "does the caller
    reach this profile" itself, following research.md R-48: a parent may
    reach any live profile on their own account; a signed-in child may
    reach only the profile their own `sign_in_user_id` names. Anything
    else is **404, not 403** — a distinguishing refusal would confirm a
    sibling's or a stranger's profile exists (FR-112, FR-132).

    Methods are grouped by the task that introduced them: `list_profiles`
    through `remove_profile` are T347 (US9); `add_trainer` and
    `remove_trainer` are T352 (US10), added to this same file afterwards
    per tasks.md's file-ordering note. `update_profile` and
    `remove_profile` are extended again by T371/T375 (US11) to also touch
    a child's own sign-in — `update_profile` is the one writer of the
    name copy data-model.md §26.1 requires, and `remove_profile` ends a
    sign-in rather than let it outlive the player (FR-135).
    """

    def __init__(
        self,
        db_session: AsyncSession,
        settings: Settings,
        photo_storage: PhotoStorage,
        share_links: ShareLinkService,
    ) -> None:
        self._settings = settings
        self._photo_storage = photo_storage
        self._profiles = PlayerProfileRepository(db_session)
        self._associations = AssociationRepository(db_session)
        self._users = UserRepository(db_session)
        self._sessions = SessionRepository(db_session)
        self._availability = AvailabilityRepository(db_session)
        self._share_links = share_links

    # --- reachability (research.md R-48) --------------------------------

    async def _own_child_profile(self, user: User) -> PlayerProfileModel | None:
        """Non-`None` exactly when `user` is a signed-in child (research.md
        R-38) — the one profile their own sign-in names."""
        return await self._profiles.get_by_sign_in_user_id(user.id)

    async def _resolve_reachable(self, user: User, profile_id: str) -> PlayerProfileModel:
        profile = await self._profiles.get_by_id(profile_id)
        if profile is None or profile.removed_at is not None:
            raise PlayerProfileNotFound("No such player profile.")

        child_profile = await self._own_child_profile(user)
        if child_profile is not None:
            if profile.id != child_profile.id:
                raise PlayerProfileNotFound("No such player profile.")
            return profile

        if profile.account_user_id != user.id:
            raise PlayerProfileNotFound("No such player profile.")
        return profile

    async def resolve_reachable_profile_id(self, user: User, profile_id: str) -> str:
        """The one thing `/me/players/{profile_id}/availability` needs
        from this service (research.md R2-11, data-model.md §111.2's
        `AvailabilityService` deliberately does no authorization of its
        own): confirms the caller may reach this profile — a parent to
        any of their own, or a signed-in child to their own — raising
        `PlayerProfileNotFound` (404, never 403) otherwise, exactly as
        every other `/me/players/{profile_id}` route already behaves.
        Returns the id only; the availability endpoints have no further
        use for the profile row itself."""
        profile = await self._resolve_reachable(user, profile_id)
        return profile.id

    # --- reads ------------------------------------------------------------

    async def list_profiles(self, user: User) -> PlayerProfileList:
        child_profile = await self._own_child_profile(user)
        profiles = (
            [child_profile]
            if child_profile is not None
            else await self._profiles.list_live_for_account(user.id)
        )
        return PlayerProfileList(profiles=[await self._to_out(p) for p in profiles])

    async def get_profile(self, user: User, profile_id: str) -> PlayerProfileOut:
        profile = await self._resolve_reachable(user, profile_id)
        return await self._to_out(profile)

    # --- create (US9, FR-106 - FR-110, FR-122, FR-123) ---------------------

    async def create_child(self, user: User, body: CreateChildProfileRequest) -> PlayerProfileOut:
        if await self._own_child_profile(user) is not None:
            raise PermissionDenied("A signed-in child cannot own a player profile.")

        if not body.acknowledge_possible_duplicate:
            duplicates = await self._profiles.find_possible_duplicate(
                account_user_id=user.id,
                first_name=body.first_name,
                last_name=body.last_name,
                date_of_birth=body.date_of_birth,
            )
            if duplicates:
                raise PossibleDuplicateProfile(
                    "A player with this name and date of birth already exists on this "
                    "account. Resend with acknowledge_possible_duplicate: true to add "
                    "them anyway.",
                    matches=[(await self._to_out(p)).model_dump(mode="json") for p in duplicates],
                )

        # FR-122/FR-123: each named trainer must be one the account
        # already trains with through *some* profile — validated across
        # every profile on the account, not only the one being created.
        # De-duplicated, order preserved, so a repeated id is not a
        # second association attempt.
        trainer_ids = list(dict.fromkeys(body.trainer_ids))
        if trainer_ids:
            account_rows = await self._associations.list_active_for_account(user.id)
            reachable_trainer_ids = {trainer.id for _, _, trainer, _ in account_rows}
            unknown = [t for t in trainer_ids if t not in reachable_trainer_ids]
            if unknown:
                raise NotFound("No such trainer among those this account already trains with.")

        profile = await self._profiles.insert(
            account_user_id=user.id,
            kind=PlayerProfileKind.CHILD.value,
            first_name=body.first_name,
            last_name=body.last_name,
            date_of_birth=body.date_of_birth,
            gender=body.gender.value,
            school=body.school,
            jersey_number=body.jersey_number,
        )

        for trainer_id in trainer_ids:
            await self._associations.insert(
                trainer_user_id=trainer_id, player_profile_id=profile.id, share_link_id=None
            )

        return await self._to_out(profile)

    # --- update (FR-107, FR-131, FR-132, FR-147, research.md R-37) --------

    async def update_profile(
        self, user: User, profile_id: str, updates: dict[str, object]
    ) -> PlayerProfileOut:
        profile = await self._resolve_reachable(user, profile_id)

        if await self._own_child_profile(user) is not None:
            # A signed-in child reaches only their own profile (checked
            # above); FR-131/FR-132 permit nothing through this endpoint
            # at all for them — their own photo goes through the photo
            # endpoint instead, which carries no other field.
            if updates:
                raise ParentOnlyField("Only a parent can change this setting.")
            return await self._to_out(profile)

        kind = PlayerProfileKind(profile.kind)
        if self_profile_rejects_names(
            kind, has_first_name="first_name" in updates, has_last_name="last_name" in updates
        ):
            raise ValidationFailure(
                "The account holder's name belongs to the account, not the profile.",
                fields={
                    field: "This field cannot be set on the account holder's own profile."
                    for field in ("first_name", "last_name")
                    if field in updates
                },
            )

        if "date_of_birth" in updates:
            new_dob = updates["date_of_birth"]
            assert isinstance(new_dob, date)
            age = age_on(new_dob, today=utcnow().date())
            if not is_valid_age_for_kind(kind, age):
                raise ValidationFailure(
                    "This date of birth is outside the allowed age range.",
                    fields={"date_of_birth": "Outside the allowed age range for this profile."},
                )

        for field in (
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "school",
            "jersey_number",
            "tokens_without_approval",
        ):
            if field not in updates:
                continue
            value = updates[field]
            if field == "gender" and value is not None and hasattr(value, "value"):
                value = value.value
            setattr(profile, field, value)
        profile.updated_at = utcnow()

        # data-model.md §26.1: `player_profiles` is authoritative for a
        # child's name, but a child who holds a sign-in also has a
        # `user_profiles` row of their own (the account invariant,
        # data-model.md §3, requires a non-null name there). This is the
        # ONE writer of that copy — no other code path may write a child
        # account's `user_profiles` names — so a name change here must
        # land on both rows in this same transaction, or the two would
        # silently drift apart the next time this profile is displayed
        # through the child's own account rather than through the
        # parent's roster.
        if profile.sign_in_user_id is not None and (
            "first_name" in updates or "last_name" in updates
        ):
            child_account_profile = await self._users.get_profile(profile.sign_in_user_id)
            assert child_account_profile is not None
            if "first_name" in updates:
                assert profile.first_name is not None
                child_account_profile.first_name = profile.first_name
            if "last_name" in updates:
                assert profile.last_name is not None
                child_account_profile.last_name = profile.last_name
            child_account_profile.updated_at = utcnow()

        return await self._to_out(profile)

    # --- remove (FR-111, FR-135) -------------------------------------------

    async def remove_profile(self, user: User, profile_id: str) -> None:
        if await self._own_child_profile(user) is not None:
            raise PermissionDenied("A signed-in child cannot remove a player profile.")
        profile = await self._resolve_reachable(user, profile_id)

        # FR-135: a credential must never outlive the player it belongs
        # to, and removal "MUST NOT allow a child account to convert
        # itself into an independent account" — clearing `sign_in_user_id`
        # alone would leave an ordinary, still-Active account able to sign
        # in again with its existing password, which is exactly that
        # conversion. The child's own `status` is what research.md R-50
        # reserves for the child's own lifecycle (as distinct from the
        # parent-derived suspension `AuthService` checks), so ending the
        # sign-in here transitions it, the same mechanism
        # `ChildSigninService.revoke` uses (FR-134) and the one every
        # other "this account no longer works" case in this codebase
        # already uses. Done before the soft removal below, in the same
        # transaction, so a removed profile is never left pointing at a
        # still-usable sign-in.
        if profile.sign_in_user_id is not None:
            child_user_id = profile.sign_in_user_id
            profile.sign_in_user_id = None
            await self._sessions.revoke_all_for_user(child_user_id)

            child_user = await self._users.get_by_id(child_user_id)
            if child_user is not None and child_user.status_enum is AccountStatus.ACTIVE:
                self._users.apply_status_change(
                    child_user,
                    target_status=AccountStatus.INACTIVE,
                    expected_version=child_user.version,
                )

        # data-model.md §114, FR-039: a removed profile's stated times must
        # not survive it — no route may still return them. The
        # `availability_updated_at` stamp on the profile row itself is left
        # as-is (removal is soft; the row and its history persist), only
        # the slot rows are deleted, in this same transaction.
        await self._availability.delete_for_owner(profile_id=profile.id)

        await self._profiles.soft_remove(profile)

    # --- photo (FR-034, FR-131, FR-132, research.md R-07, R-37) ------------

    async def upload_photo(self, user: User, profile_id: str, data: bytes) -> PhotoUrls:
        profile = await self._resolve_reachable(user, profile_id)

        if profile.kind == PlayerProfileKind.SELF.value:
            raise ValidationFailure(
                "The account holder's own profile has no photo of its own. "
                "Use PUT /me/profile/photo instead.",
                fields={"file": "Not accepted for the account holder's own profile."},
            )

        if len(data) > self._settings.max_upload_bytes:
            raise PayloadTooLarge("Upload a JPEG, PNG, or WebP image no larger than 5 MB.")

        try:
            image, extension = decode_and_validate(data)
        except UnsupportedImageError as exc:
            raise UnsupportedMediaType(
                "Upload a JPEG, PNG, or WebP image no larger than 5 MB."
            ) from exc

        previous_key = profile.photo_key
        new_key = f"{new_uuid()}.{extension}"
        await self._photo_storage.save(new_key, encode(image, extension))
        await self._photo_storage.save(thumbnail_key_for(new_key), make_thumbnail(image, extension))

        profile.photo_key = new_key
        profile.updated_at = utcnow()

        if previous_key:
            await self._photo_storage.delete(previous_key)
            await self._photo_storage.delete(thumbnail_key_for(previous_key))

        return PhotoUrls(
            photo_url=f"/media/photos/{new_key}",
            thumbnail_url=f"/media/photos/{new_key}?variant=thumb",
        )

    # --- trainers (US10, FR-124 - FR-128) -----------------------------------

    async def add_trainer(
        self, user: User, profile_id: str, body: AddPlayerTrainerRequest
    ) -> PlayerProfileOut:
        if await self._own_child_profile(user) is not None:
            raise PermissionDenied("A signed-in child cannot change any association.")
        profile = await self._resolve_reachable(user, profile_id)

        share_link_id: str | None = None
        used_link = None
        if body.code is not None:
            used_link, trainer = await self._share_links.resolve_usable_link(body.code)
            trainer_id = trainer.id
            share_link_id = used_link.id
        else:
            assert body.trainer_id is not None
            trainer_id = body.trainer_id
            account_rows = await self._associations.list_active_for_account(user.id)
            reachable_trainer_ids = {t.id for _, _, t, _ in account_rows}
            if trainer_id not in reachable_trainer_ids:
                raise NotFound("No such trainer among those this account already trains with.")

        existing = await self._associations.get(
            trainer_user_id=trainer_id, player_profile_id=profile.id
        )
        if existing is None:
            await self._associations.insert(
                trainer_user_id=trainer_id,
                player_profile_id=profile.id,
                share_link_id=share_link_id,
            )
            if used_link is not None:
                await self._share_links.record_use(used_link)
        elif existing.status != AssociationStatus.ACTIVE.value:
            # FR-127: re-adding a previously removed trainer reuses the
            # same association row and its earlier history, rather than
            # inserting a duplicate (the unique (trainer, profile) pair
            # would refuse a second row anyway).
            existing.status = AssociationStatus.ACTIVE.value
            existing.updated_at = utcnow()
            if share_link_id is not None:
                existing.share_link_id = share_link_id
            if used_link is not None:
                await self._share_links.record_use(used_link)
        # else: already active — idempotent no-op, writes nothing (FR-125,
        # Story 10 scenario 4).

        return await self._to_out(profile)

    async def remove_trainer(self, user: User, profile_id: str, association_id: str) -> None:
        if await self._own_child_profile(user) is not None:
            raise PermissionDenied("A signed-in child cannot change any association.")
        profile = await self._resolve_reachable(user, profile_id)

        association = await self._associations.get_by_id(association_id)
        if association is None or association.player_profile_id != profile.id:
            raise NotFound("No such association on a profile you own.")

        # Soft — never deleted, so every historical record survives
        # (FR-126). A later add_trainer for the same pair reactivates
        # this same row (FR-127).
        association.status = AssociationStatus.INACTIVE.value
        association.updated_at = utcnow()

    # --- serialization ------------------------------------------------------

    async def _to_out(self, profile: PlayerProfileModel) -> PlayerProfileOut:
        if profile.kind == PlayerProfileKind.CHILD.value:
            display_name = f"{profile.first_name} {profile.last_name}"
            photo_url = f"/media/photos/{profile.photo_key}" if profile.photo_key else None
        else:
            # A SELF profile's name and photo are the account's, never
            # its own (research.md R-37).
            account_profile = await self._users.get_profile(profile.account_user_id)
            assert account_profile is not None
            display_name = f"{account_profile.first_name} {account_profile.last_name}"
            photo_url = (
                f"/media/photos/{account_profile.photo_key}" if account_profile.photo_key else None
            )

        rows = await self._associations.list_active_for_player(profile.id)
        associations = []
        for association, trainer_user, _trainer_profile in rows:
            trainer_org = await self._users.get_role_detail(trainer_user)
            business_name = (
                trainer_org.business_name if isinstance(trainer_org, TrainerOrganization) else ""
            )
            associations.append(
                PlayerProfileAssociation(
                    association_id=association.id,
                    trainer_id=trainer_user.id,
                    trainer_display_name=business_name,
                    joined_at=association.joined_at,
                )
            )

        age = (
            age_on(profile.date_of_birth, today=utcnow().date())
            if profile.date_of_birth is not None
            else None
        )

        return PlayerProfileOut(
            id=profile.id,
            kind=PlayerProfileKind(profile.kind),
            display_name=display_name,
            first_name=profile.first_name,
            last_name=profile.last_name,
            date_of_birth=profile.date_of_birth,
            age=age,
            gender=profile.gender,
            school=profile.school,
            jersey_number=profile.jersey_number,
            skill_level=profile.skill_level,
            photo_url=photo_url,
            tokens_without_approval=profile.tokens_without_approval,
            has_sign_in=profile.sign_in_user_id is not None,
            associations=associations,
        )
