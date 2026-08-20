import io

from PIL import Image, UnidentifiedImageError

THUMBNAIL_SIZE = (128, 128)

_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
_FORMAT_TO_EXTENSION = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class UnsupportedImageError(Exception):
    pass


def decode_and_validate(data: bytes) -> tuple[Image.Image, str]:
    """Determines the image format by decoding the bytes — never by a
    declared content type or filename extension, so a renamed non-image
    file cannot pass (research.md R-07). Returns the decoded image and
    its file extension."""
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise UnsupportedImageError("Not a decodable image.") from exc

    if image.format not in _ALLOWED_FORMATS:
        raise UnsupportedImageError(f"Unsupported image format: {image.format}")

    return image, _FORMAT_TO_EXTENSION[image.format]


def encode(image: Image.Image, image_format: str) -> bytes:
    buffer = io.BytesIO()
    save_format = "JPEG" if image_format == "jpg" else image_format.upper()
    if save_format == "JPEG" and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(buffer, format=save_format)
    return buffer.getvalue()


def make_thumbnail(image: Image.Image, image_format: str) -> bytes:
    thumbnail = image.copy()
    thumbnail.thumbnail(THUMBNAIL_SIZE)
    return encode(thumbnail, image_format)
