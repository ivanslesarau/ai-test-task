import pytest

from app.core.errors import ValidationFailure
from app.models.enums import UserRole
from app.services.profile_service import _normalize_phone, editable_fields_for


def test_common_fields_are_editable_by_every_role() -> None:
    for role in UserRole:
        assert {"first_name", "last_name", "phone"} <= editable_fields_for(role)


def test_coach_cannot_write_player_fields() -> None:
    coach_fields = editable_fields_for(UserRole.COACH)
    assert "jersey_number" not in coach_fields
    assert "school" not in coach_fields


def test_no_role_can_write_skill_level() -> None:
    """FR-007: skill_level is never in any role's editable set — it isn't
    even offered as a field to reject via the allow-list check, it's
    caught earlier by the always-forbidden list."""
    for role in UserRole:
        assert "skill_level" not in editable_fields_for(role)


def test_super_admin_has_no_role_specific_fields() -> None:
    assert editable_fields_for(UserRole.SUPER_ADMIN) == {"first_name", "last_name", "phone"}


def test_trainer_fields_are_role_specific() -> None:
    fields = editable_fields_for(UserRole.TRAINER)
    assert "business_name" in fields
    assert "bio" not in fields


def test_normalize_phone_accepts_e164_and_reformats_us_local() -> None:
    assert _normalize_phone("+14155552671") == "+14155552671"
    assert _normalize_phone("4155552671") == "+14155552671"


def test_normalize_phone_rejects_garbage() -> None:
    with pytest.raises(ValidationFailure):
        _normalize_phone("not-a-phone-number")
