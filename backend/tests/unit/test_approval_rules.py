"""The Pending Parent Approval rule matrix (US12, tasks.md T389). SC-035,
SC-036, and SC-037 are measured by this file: whether approval is
required at all, and every permitted and forbidden status transition
from data-model.md §25."""

import itertools

import pytest

from app.core.errors import ApprovalAmountChanged
from app.models.enums import ApprovalRequestStatus, is_approval_transition_allowed
from app.services.approval_service import approval_required, check_amount_unchanged

# FR-145: USD always requires approval, under every state of the setting.


@pytest.mark.parametrize("tokens_without_approval", [True, False])
def test_usd_payment_always_requires_approval(tokens_without_approval: bool) -> None:
    from app.models.enums import ApprovalRequestKind

    assert (
        approval_required(
            ApprovalRequestKind.USD_PAYMENT, tokens_without_approval=tokens_without_approval
        )
        is True
    )


# FR-146: a token spend requires approval exactly when the setting is off.


def test_token_spend_requires_approval_when_setting_is_off() -> None:
    from app.models.enums import ApprovalRequestKind

    assert (
        approval_required(ApprovalRequestKind.TOKEN_SPEND, tokens_without_approval=False) is True
    )


def test_token_spend_does_not_require_approval_when_setting_is_on() -> None:
    from app.models.enums import ApprovalRequestKind

    assert (
        approval_required(ApprovalRequestKind.TOKEN_SPEND, tokens_without_approval=True) is False
    )


# FR-137/FR-138: join_trainer always requires approval — it is the only
# path that raises this kind, and it exists precisely because the child
# was blocked.


@pytest.mark.parametrize("tokens_without_approval", [True, False])
def test_join_trainer_always_requires_approval(tokens_without_approval: bool) -> None:
    from app.models.enums import ApprovalRequestKind

    assert (
        approval_required(
            ApprovalRequestKind.JOIN_TRAINER, tokens_without_approval=tokens_without_approval
        )
        is True
    )


# FR-152: an approved financial request whose amount changed since it was shown.


def test_check_amount_unchanged_passes_when_amounts_match() -> None:
    check_amount_unchanged(recorded_amount_minor=500, shown_amount_minor=500)


def test_check_amount_unchanged_raises_when_amounts_differ() -> None:
    with pytest.raises(ApprovalAmountChanged):
        check_amount_unchanged(recorded_amount_minor=500, shown_amount_minor=600)


# FR-143, data-model.md §25: every permitted and forbidden transition.

_PERMITTED = {
    (ApprovalRequestStatus.PENDING_PARENT_APPROVAL, ApprovalRequestStatus.INFO_REQUESTED),
    (ApprovalRequestStatus.PENDING_PARENT_APPROVAL, ApprovalRequestStatus.APPROVED),
    (ApprovalRequestStatus.PENDING_PARENT_APPROVAL, ApprovalRequestStatus.DENIED),
    (ApprovalRequestStatus.PENDING_PARENT_APPROVAL, ApprovalRequestStatus.EXPIRED),
    (ApprovalRequestStatus.PENDING_PARENT_APPROVAL, ApprovalRequestStatus.WITHDRAWN),
    (ApprovalRequestStatus.INFO_REQUESTED, ApprovalRequestStatus.PENDING_PARENT_APPROVAL),
    (ApprovalRequestStatus.INFO_REQUESTED, ApprovalRequestStatus.DENIED),
    (ApprovalRequestStatus.INFO_REQUESTED, ApprovalRequestStatus.EXPIRED),
    (ApprovalRequestStatus.INFO_REQUESTED, ApprovalRequestStatus.WITHDRAWN),
}

_ALL_PAIRS = {
    (a, b) for a, b in itertools.product(ApprovalRequestStatus, ApprovalRequestStatus) if a != b
}


@pytest.mark.parametrize("current,target", sorted(_PERMITTED))
def test_permitted_transition_is_allowed(
    current: ApprovalRequestStatus, target: ApprovalRequestStatus
) -> None:
    assert is_approval_transition_allowed(current, target) is True


@pytest.mark.parametrize("current,target", sorted(_ALL_PAIRS - _PERMITTED))
def test_forbidden_transition_is_not_allowed(
    current: ApprovalRequestStatus, target: ApprovalRequestStatus
) -> None:
    assert is_approval_transition_allowed(current, target) is False


def test_info_requested_cannot_go_straight_to_approved() -> None:
    """The transition table's deliberate omission: a parent's question
    must be answered before it can be approved, never skipped straight
    to a decision."""
    assert (
        is_approval_transition_allowed(
            ApprovalRequestStatus.INFO_REQUESTED, ApprovalRequestStatus.APPROVED
        )
        is False
    )
