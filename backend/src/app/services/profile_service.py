from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import (
    ActionNotPermitted,
    PayloadTooLarge,
    UnsupportedMediaType,
    ValidationFailure,
)
from app.core.phone import normalize_phone
from app.db.base import new_uuid, utcnow
from app.models.enums import AccountStatus, UserRole
from app.models.role_details import CoachDetail, ParentContact, TrainerOrganization
from app.models.user import User
from app.repositories.player_profile_repository import PlayerProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.profile import OwnProfile, PhotoUrls
from app.schemas.role_detail import build_role_detail_out
from app.services.image_processing import (
    UnsupportedImageError,
    decode_and_validate,
    encode,
    make_thumbnail,
)
from app.services.ports.photo_storage import PhotoStorage, thumbnail_key_for

# FR-033: identity/classification fields are read-only in the profile,
# regardless of role, and rejecting an attempt to write one is required —
# not silently ignoring it.
_NEVER_EDITABLE = frozenset({"email", "role", "status", "created_at", "skill_level"})

_COMMON_EDITABLE = frozenset({"first_name", "last_name", "phone"})

_ROLE_EDITABLE: dict[UserRole, frozenset[str]] = {
    UserRole.SUPER_ADMIN: frozenset(),
    UserRole.TRAINER: frozenset({"business_name", "address", "website", "description"}),
    UserRole.COACH: frozenset({"bio", "credentials", "certifications", "is_publicly_visible"}),
    # `school` and `jersey_number` left the account's role detail — they
    # describe one player, and an account now holds several (data-model.md
    # §35, research.md R-34). They are edited per-profile through
    # `/me/players/{profile_id}`, not here. Only the family's one contact
    # record remains an account-level field.
    UserRole.PLAYER_PARENT: frozenset(
        {
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
        }
    ),
}


def editable_fields_for(role: UserRole) -> frozenset[str]:
    return _COMMON_EDITABLE | _ROLE_EDITABLE[role]


class ProfileService:
    def __init__(
        self,
        db_session: AsyncSession,
        settings: Settings,
        photo_storage: PhotoStorage,
    ) -> None:
        self._settings = settings
        self._photo_storage = photo_storage
        self._users = UserRepository(db_session)
        self._profiles = PlayerProfileRepository(db_session)

    async def get_own_profile(self, user: User) -> OwnProfile:
        profile = await self._users.get_profile(user.id)
        assert profile is not None
        profile_count = (
            len(await self._profiles.list_live_for_account(user.id))
            if user.role_enum is UserRole.PLAYER_PARENT
            else 0
        )
        role_detail = build_role_detail_out(
            await self._users.get_role_detail(user), profile_count=profile_count
        )
        return OwnProfile(
            id=user.id,
            email=user.email,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
            first_name=profile.first_name,
            last_name=profile.last_name,
            phone=profile.phone,
            photo_url=f"/media/photos/{profile.photo_key}" if profile.photo_key else None,
            thumbnail_url=(
                f"/media/photos/{profile.photo_key}?variant=thumb" if profile.photo_key else None
            ),
            role_detail=role_detail,
            editable_fields=sorted(editable_fields_for(user.role_enum)),
        )

    async def update_own_profile(self, user: User, updates: dict[str, object]) -> OwnProfile:
        if user.status_enum is AccountStatus.DELETED:
            raise ActionNotPermitted(
                "This account has been erased and cannot be edited.", code="erasure_is_permanent"
            )

        allowed = editable_fields_for(user.role_enum)
        rejected: dict[str, str] = {}
        for field in updates:
            if field in _NEVER_EDITABLE:
                rejected[field] = "This field cannot be changed here."
            elif field not in allowed:
                rejected[field] = "This field is not editable for your role."
        if rejected:
            raise ValidationFailure("One or more fields are invalid.", fields=rejected)

        if "phone" in updates and updates["phone"] is not None:
            updates["phone"] = normalize_phone(str(updates["phone"]))

        profile = await self._users.get_profile(user.id)
        assert profile is not None
        for field in ("first_name", "last_name", "phone"):
            if field in updates:
                setattr(profile, field, updates[field])
        profile.updated_at = utcnow()

        if user.role_enum is not UserRole.SUPER_ADMIN:
            await self._apply_role_detail_updates(user, updates)

        return await self.get_own_profile(user)

    async def _apply_role_detail_updates(self, user: User, updates: dict[str, object]) -> None:
        detail = await self._users.get_role_detail(user)
        role = user.role_enum

        if role is UserRole.TRAINER and isinstance(detail, TrainerOrganization):
            for field in ("business_name", "address", "website", "description"):
                if field in updates:
                    setattr(detail, field, updates[field])
        elif role is UserRole.COACH and isinstance(detail, CoachDetail):
            for field in ("bio", "credentials", "certifications", "is_publicly_visible"):
                if field in updates:
                    setattr(detail, field, updates[field])
        elif role is UserRole.PLAYER_PARENT and isinstance(detail, ParentContact):
            # `school`/`jersey_number` no longer route through here — they
            # are per-profile now and rejected by `editable_fields_for`
            # before this method is ever reached (data-model.md §35).
            for field in (
                "emergency_contact_name",
                "emergency_contact_phone",
                "emergency_contact_relation",
            ):
                if field in updates:
                    setattr(detail, field, updates[field])

    async def upload_own_photo(self, user: User, data: bytes) -> PhotoUrls:
        if len(data) > self._settings.max_upload_bytes:
            raise PayloadTooLarge("Upload a JPEG, PNG, or WebP image no larger than 5 MB.")

        try:
            image, extension = decode_and_validate(data)
        except UnsupportedImageError as exc:
            raise UnsupportedMediaType(
                "Upload a JPEG, PNG, or WebP image no larger than 5 MB."
            ) from exc

        profile = await self._users.get_profile(user.id)
        assert profile is not None
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

    async def delete_own_photo(self, user: User) -> None:
        profile = await self._users.get_profile(user.id)
        assert profile is not None
        if profile.photo_key:
            await self._photo_storage.delete(profile.photo_key)
            await self._photo_storage.delete(thumbnail_key_for(profile.photo_key))
            profile.photo_key = None
            profile.updated_at = utcnow()
