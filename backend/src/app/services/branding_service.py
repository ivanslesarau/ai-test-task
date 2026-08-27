from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import PayloadTooLarge, ValidationFailure
from app.db.base import new_uuid, utcnow
from app.models.enums import UserRole
from app.models.role_details import TrainerOrganization
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.branding import (
    DEFAULT_PORTAL_BRANDING,
    PortalBranding,
    build_portal_branding_out,
)
from app.services.image_processing import UnsupportedImageError, decode_and_validate, encode
from app.services.ports.photo_storage import PhotoStorage
from app.services.svg_screening import UnsafeSvgError, screen_svg
from app.services.trainer_context_service import TrainerContextService

_MAX_LOGO_DIMENSION = 200

# FR-094: 2 MB, a fixed contract value — deliberately not
# settings.max_upload_bytes, which governs the unrelated 5 MB profile
# photo limit (research.md; contracts/openapi.yaml uploadOwnLogo).
_MAX_LOGO_BYTES = 2 * 1024 * 1024


class BrandingService:
    """A trainer's portal identity: read, update, logo lifecycle, and —
    the function every other CurrentUser/preview response calls —
    resolving whose branding applies to a given viewer (FR-101)."""

    def __init__(self, db_session: AsyncSession, photo_storage: PhotoStorage) -> None:
        self._users = UserRepository(db_session)
        self._trainer_context = TrainerContextService(db_session)
        self._photo_storage = photo_storage

    async def resolve_for_viewer(self, user: User) -> PortalBranding:
        """FR-101's rule, one function: a trainer's own branding, a
        player's active context's, the platform default otherwise.

        Coach is not yet resolvable to an employer trainer — which
        trainer a coach works for is US-01.08, out of scope here — so a
        Coach receives the platform default. See research.md R-33; this
        is a known, documented gap, not an oversight."""
        if user.role_enum is UserRole.TRAINER:
            trainer_org = await self._users.get_role_detail(user)
            return build_portal_branding_out(trainer_org)

        if user.role_enum is UserRole.PLAYER_PARENT:
            active_trainer_id = await self._trainer_context.resolve_active_trainer_id(user)
            if active_trainer_id is None:
                return DEFAULT_PORTAL_BRANDING
            trainer = await self._users.get_by_id(active_trainer_id)
            if trainer is None:
                return DEFAULT_PORTAL_BRANDING
            trainer_org = await self._users.get_role_detail(trainer)
            return build_portal_branding_out(trainer_org)

        # TODO(US-01.08): once a coach's employer trainer is known, this
        # branch resolves that trainer's branding exactly as the Trainer
        # branch above does.
        return DEFAULT_PORTAL_BRANDING

    async def get_own(self, trainer: User) -> PortalBranding:
        trainer_org = await self._users.get_role_detail(trainer)
        return build_portal_branding_out(trainer_org)

    async def update_color(self, trainer: User, *, primary_color: str | None) -> PortalBranding:
        """`primary_color` is `...` (unset) only via the caller's
        `exclude_unset` dict, never reaching this signature — the router
        only calls this when the key was present, so `None` here always
        means an explicit clear (constitution Principle VI)."""
        trainer_org = await self._users.get_role_detail(trainer)
        assert isinstance(trainer_org, TrainerOrganization)
        trainer_org.primary_color = primary_color
        trainer_org.branding_updated_at = utcnow()
        return build_portal_branding_out(trainer_org)

    async def upload_logo(self, trainer: User, data: bytes) -> PortalBranding:
        if len(data) > _MAX_LOGO_BYTES:
            raise PayloadTooLarge(f"Logo must be at most {_MAX_LOGO_BYTES} bytes.")

        trainer_org = await self._users.get_role_detail(trainer)
        assert isinstance(trainer_org, TrainerOrganization)
        previous_key = trainer_org.logo_key

        # A fresh, unguessable key per upload (matching profile photos,
        # R-07) rather than one deterministic on trainer id and
        # extension — two same-extension uploads in a row must produce
        # two distinct keys, so a replacement always deletes a real
        # previous file instead of silently overwriting it in place
        # (FR-103).
        if data.lstrip()[:1] == b"<":
            # SVG path: screened, never resized (R-27) — a vector scales.
            try:
                screen_svg(data)
            except UnsafeSvgError as exc:
                raise ValidationFailure(
                    "One or more fields are invalid.", fields={"file": str(exc)}
                ) from exc
            key = f"{new_uuid()}.svg"
            await self._photo_storage.save(key, data)
        else:
            try:
                image, extension = decode_and_validate(data)
            except UnsupportedImageError as exc:
                raise ValidationFailure(
                    "One or more fields are invalid.", fields={"file": str(exc)}
                ) from exc
            if extension not in ("png", "jpg"):
                raise ValidationFailure(
                    "One or more fields are invalid.",
                    fields={"file": f"Unsupported logo format: {extension}"},
                )
            if image.width > _MAX_LOGO_DIMENSION or image.height > _MAX_LOGO_DIMENSION:
                image = image.copy()
                image.thumbnail((_MAX_LOGO_DIMENSION, _MAX_LOGO_DIMENSION))
            key = f"{new_uuid()}.{extension}"
            await self._photo_storage.save(key, encode(image, extension))

        trainer_org.logo_key = key
        trainer_org.branding_updated_at = utcnow()

        if previous_key and previous_key != key:
            await self._photo_storage.delete(previous_key)

        return build_portal_branding_out(trainer_org)

    async def delete_logo(self, trainer: User) -> None:
        trainer_org = await self._users.get_role_detail(trainer)
        assert isinstance(trainer_org, TrainerOrganization)
        if trainer_org.logo_key:
            await self._photo_storage.delete(trainer_org.logo_key)
        trainer_org.logo_key = None
        trainer_org.branding_updated_at = utcnow()

    async def reset(self, trainer: User) -> PortalBranding:
        trainer_org = await self._users.get_role_detail(trainer)
        assert isinstance(trainer_org, TrainerOrganization)
        if trainer_org.logo_key:
            await self._photo_storage.delete(trainer_org.logo_key)
        trainer_org.logo_key = None
        trainer_org.primary_color = None
        trainer_org.branding_updated_at = utcnow()
        return build_portal_branding_out(trainer_org)
