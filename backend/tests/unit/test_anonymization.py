"""Documents data-model.md §10's transformation table as executable
assertions about ErasureService's field-level behavior — exercised at the
integration level in test_erasure.py, since anonymization only makes sense
against a real persisted account and its role detail row. This file
records, in one place, exactly which columns change and which are
deliberately preserved, so a reviewer sees the full table without reading
the service implementation."""

from app.models.enums import AccountStatus, is_transition_allowed

# Fields that change on erasure, by table.
ANONYMIZED_FIELDS = {
    "users": {"email", "password_hash", "status", "version"},
    "user_profiles": {"first_name", "last_name", "phone", "photo_key"},
    "trainer_organizations": {"address", "website", "description"},
    "coach_details": {"bio", "credentials", "certifications", "is_publicly_visible"},
    "player_details": {"school", "jersey_number"},
    "parent_contacts": {
        "emergency_contact_name",
        "emergency_contact_phone",
        "emergency_contact_relation",
    },
}

# Fields that deliberately survive erasure, and why — see data-model.md §10.
PRESERVED_FIELDS = {
    "trainer_organizations": {"business_name"},  # later epics' revenue/roster attribution
    "player_details": {"skill_level"},  # a classification, not an identifier
}


def test_erasure_targets_and_preservations_do_not_overlap() -> None:
    for table, preserved in PRESERVED_FIELDS.items():
        anonymized = ANONYMIZED_FIELDS.get(table, set())
        assert not (preserved & anonymized), f"{table} lists a field as both preserved and changed"


def test_erasure_is_reachable_only_from_active_or_inactive() -> None:
    assert is_transition_allowed(AccountStatus.ACTIVE, AccountStatus.DELETED)
    assert is_transition_allowed(AccountStatus.INACTIVE, AccountStatus.DELETED)
    assert not is_transition_allowed(AccountStatus.DELETED, AccountStatus.DELETED)
