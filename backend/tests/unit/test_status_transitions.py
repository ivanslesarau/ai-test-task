import itertools

import pytest

from app.models.enums import AccountStatus, is_transition_allowed


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (AccountStatus.ACTIVE, AccountStatus.INACTIVE),
        (AccountStatus.INACTIVE, AccountStatus.ACTIVE),
        (AccountStatus.ACTIVE, AccountStatus.DELETED),
        (AccountStatus.INACTIVE, AccountStatus.DELETED),
    ],
)
def test_allowed_transitions(current: AccountStatus, target: AccountStatus) -> None:
    assert is_transition_allowed(current, target) is True


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (AccountStatus.DELETED, AccountStatus.ACTIVE),
        (AccountStatus.DELETED, AccountStatus.INACTIVE),
        (AccountStatus.ACTIVE, AccountStatus.ACTIVE),
        (AccountStatus.INACTIVE, AccountStatus.INACTIVE),
        (AccountStatus.DELETED, AccountStatus.DELETED),
    ],
)
def test_disallowed_transitions(current: AccountStatus, target: AccountStatus) -> None:
    assert is_transition_allowed(current, target) is False


def test_every_pair_is_explicitly_classified() -> None:
    """No pair silently falls through — every combination of statuses is
    either in the allow-list or is correctly rejected (FR-003)."""
    all_pairs = set(itertools.product(AccountStatus, AccountStatus))
    allowed = {p for p in all_pairs if is_transition_allowed(*p)}
    assert allowed == {
        (AccountStatus.ACTIVE, AccountStatus.INACTIVE),
        (AccountStatus.INACTIVE, AccountStatus.ACTIVE),
        (AccountStatus.ACTIVE, AccountStatus.DELETED),
        (AccountStatus.INACTIVE, AccountStatus.DELETED),
    }
