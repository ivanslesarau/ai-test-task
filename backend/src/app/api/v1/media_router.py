from typing import Annotated, Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.deps import CurrentUserDep, PhotoStorageDep
from app.core.errors import NotFound
from app.services.ports.photo_storage import thumbnail_key_for

router = APIRouter(prefix="/media", tags=["media"])

_CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


@router.get("/photos/{key}")
async def get_photo(
    key: str,
    _user: CurrentUserDep,
    photo_storage: PhotoStorageDep,
    variant: Annotated[Literal["original", "thumb"], Query()] = "original",
) -> Response:
    """Served through the application, not a static mount, so the session
    check lives in one place and the storage layout stays private
    (contracts/openapi.yaml)."""
    lookup_key = thumbnail_key_for(key) if variant == "thumb" else key
    data = await photo_storage.read(lookup_key)
    if data is None:
        raise NotFound("No such photo.")

    extension = key.rsplit(".", 1)[-1].lower()
    content_type = _CONTENT_TYPES.get(extension, "application/octet-stream")
    return Response(content=data, media_type=content_type)


_BRANDING_CONTENT_TYPES = {**_CONTENT_TYPES, "svg": "image/svg+xml"}


@router.get("/branding/{key}")
async def get_branding_logo(key: str, photo_storage: PhotoStorageDep) -> Response:
    """**Unauthenticated**, unlike /photos/{key} — FR-073 puts a
    trainer's branding on the join page, reached before anyone has an
    account. SVG responses carry nosniff and a locked-down CSP; clients
    must render logos through <img> only, never <object>/<embed>/inline
    (research.md R-27) — that layer is what holds even if this one is
    wrong."""
    data = await photo_storage.read(key)
    if data is None:
        raise NotFound("No such logo.")

    extension = key.rsplit(".", 1)[-1].lower()
    content_type = _BRANDING_CONTENT_TYPES.get(extension, "application/octet-stream")
    headers = {"X-Content-Type-Options": "nosniff"}
    if extension == "svg":
        headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
    return Response(content=data, media_type=content_type, headers=headers)
