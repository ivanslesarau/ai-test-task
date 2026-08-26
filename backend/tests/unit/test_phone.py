import pytest

from app.core.errors import ValidationFailure
from app.core.phone import normalize_phone


def test_a_parseable_international_number_normalizes_to_e164() -> None:
    assert normalize_phone("+1 (415) 555-2671") == "+14155552671"


def test_an_unparseable_string_raises_attributed_to_phone() -> None:
    with pytest.raises(ValidationFailure) as excinfo:
        normalize_phone("not-a-phone-number")
    assert "phone" in excinfo.value.fields


def test_a_valid_looking_but_invalid_number_raises_attributed_to_phone() -> None:
    with pytest.raises(ValidationFailure) as excinfo:
        normalize_phone("+1123")
    assert "phone" in excinfo.value.fields


def test_the_empty_string_is_rejected_rather_than_crashing() -> None:
    with pytest.raises(ValidationFailure) as excinfo:
        normalize_phone("")
    assert "phone" in excinfo.value.fields


def test_a_whitespace_only_string_is_rejected() -> None:
    with pytest.raises(ValidationFailure):
        normalize_phone("   ")
