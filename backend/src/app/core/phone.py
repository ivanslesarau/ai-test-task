"""Phone parsing and E.164 normalization.

The one place either write path (own-profile update, admin user creation)
turns a phone number into its canonical form. Both paths must apply the
identical rule (FR-022, data-model.md §12), so this lives outside either
service.
"""

import phonenumbers
from phonenumbers import NumberParseException

from app.core.errors import ValidationFailure

_INVALID_PHONE_MESSAGE = "Enter a valid phone number."


def normalize_phone(raw: str) -> str:
    """Parses `raw` as an international phone number and returns its E.164
    form. Raises `ValidationFailure`, attributed to `phone`, for a string
    that does not parse, is not a valid number, or is empty/whitespace —
    the empty string is rejected here rather than crashing inside
    `phonenumbers.parse`."""
    if not raw.strip():
        raise ValidationFailure(
            "One or more fields are invalid.", fields={"phone": _INVALID_PHONE_MESSAGE}
        )
    try:
        parsed = phonenumbers.parse(raw, region=None)
    except NumberParseException as exc:
        raise ValidationFailure(
            "One or more fields are invalid.", fields={"phone": _INVALID_PHONE_MESSAGE}
        ) from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationFailure(
            "One or more fields are invalid.", fields={"phone": _INVALID_PHONE_MESSAGE}
        )
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
