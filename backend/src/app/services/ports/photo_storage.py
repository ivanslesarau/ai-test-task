import asyncio
from pathlib import Path
from typing import Protocol


class PhotoStorage(Protocol):
    async def save(self, key: str, data: bytes) -> None: ...
    async def read(self, key: str) -> bytes | None: ...
    async def delete(self, key: str) -> None: ...


class LocalPhotoStorage:
    """Local filesystem implementation, keyed by an unguessable name
    (research.md R-07). Suitable for this feature's single-host SQLite
    deployment; swappable for object storage behind this same interface
    at multi-host scale."""

    def __init__(self, upload_dir: str) -> None:
        self._upload_dir = Path(upload_dir)

    def _path_for(self, key: str) -> Path:
        # Reject any key that could escape the upload directory — this
        # storage is keyed by server-generated names only, never by
        # client-supplied input, but this guard costs nothing and closes
        # the path-traversal class of bug outright.
        if "/" in key or "\\" in key or key in {".", ".."}:
            raise ValueError(f"Invalid photo storage key: {key!r}")
        return self._upload_dir / key

    async def save(self, key: str, data: bytes) -> None:
        def _write() -> None:
            self._upload_dir.mkdir(parents=True, exist_ok=True)
            self._path_for(key).write_bytes(data)

        await asyncio.to_thread(_write)

    async def read(self, key: str) -> bytes | None:
        def _read() -> bytes | None:
            path = self._path_for(key)
            if not path.exists():
                return None
            return path.read_bytes()

        return await asyncio.to_thread(_read)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(lambda: self._path_for(key).unlink(missing_ok=True))


def get_photo_storage(upload_dir: str) -> PhotoStorage:
    return LocalPhotoStorage(upload_dir)


def thumbnail_key_for(photo_key: str) -> str:
    """The thumbnail is stored under a deterministic name derived from the
    original's key, so `?variant=thumb` (contracts/openapi.yaml) can
    resolve it without a second column on `user_profiles` — only
    `photo_key` itself needs to be persisted."""
    stem, _, extension = photo_key.rpartition(".")
    return f"{stem}-thumb.{extension}"
