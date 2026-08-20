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
