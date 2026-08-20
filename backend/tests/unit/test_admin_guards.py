from app.models.enums import AccountStatus, is_transition_allowed


def test_active_to_inactive_is_a_valid_transition_for_deactivation() -> None:
    assert is_transition_allowed(AccountStatus.ACTIVE, AccountStatus.INACTIVE)


def test_inactive_to_active_is_a_valid_transition_for_reactivation() -> None:
    assert is_transition_allowed(AccountStatus.INACTIVE, AccountStatus.ACTIVE)


def test_deleted_cannot_transition_anywhere() -> None:
    assert not is_transition_allowed(AccountStatus.DELETED, AccountStatus.ACTIVE)
    assert not is_transition_allowed(AccountStatus.DELETED, AccountStatus.INACTIVE)


def test_deactivating_an_already_inactive_account_is_not_a_valid_transition() -> None:
    """No pair transitions to itself — this is what makes
    "deactivate an already-Inactive account" a no-op refusal rather than
    a second deactivation record."""
    assert not is_transition_allowed(AccountStatus.INACTIVE, AccountStatus.INACTIVE)
