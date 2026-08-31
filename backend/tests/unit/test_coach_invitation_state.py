"""US1 (tasks.md T517): the presented-state precedence of data-model.md
§101.1 — accepted > revoked > superseded > expired > blocked > awaiting —
and the usability predicate of §101.2, which deliberately ignores
`blocked_at` (FR-015).
"""

from datetime import timedelta

from app.db.base import new_uuid, utcnow
from app.models.coach_invitation import CoachInvitation
from app.models.enums import CoachInvitationBlockReason, CoachInvitationState
from app.repositories.coach_invitation_repository import CoachInvitationRepository
from app.services.coach_invitation_service import CoachInvitationService


def _invitation(**overrides: object) -> CoachInvitation:
    now = utcnow()
    defaults: dict[str, object] = dict(
        id=new_uuid(),
        trainer_user_id=new_uuid(),
        created_by_user_id=new_uuid(),
        token_hash="a" * 64,
        invited_email="coach@example.org",
        invitee_name=None,
        message=None,
        state=CoachInvitationState.AWAITING.value,
        issued_at=now,
        expires_at=now + timedelta(days=7),
        accepted_by_user_id=None,
        accepted_at=None,
        revoked_at=None,
        superseded_at=None,
        superseded_by_id=None,
        blocked_at=None,
        blocked_reason=None,
    )
    defaults.update(overrides)
    return CoachInvitation(**defaults)


def test_accepted_outranks_every_other_signal() -> None:
    now = utcnow()
    invitation = _invitation(
        state=CoachInvitationState.ACCEPTED.value,
        accepted_by_user_id=new_uuid(),
        accepted_at=now,
        expires_at=now - timedelta(days=1),
        blocked_at=now,
        blocked_reason=CoachInvitationBlockReason.ALREADY_ASSIGNED.value,
    )
    assert CoachInvitationService.presented_state(invitation, now=now) == "accepted"


def test_revoked_outranks_superseded_expired_and_blocked() -> None:
    now = utcnow()
    invitation = _invitation(
        state=CoachInvitationState.REVOKED.value, revoked_at=now, expires_at=now - timedelta(days=1)
    )
    assert CoachInvitationService.presented_state(invitation, now=now) == "revoked"


def test_superseded_outranks_expired_and_blocked() -> None:
    now = utcnow()
    invitation = _invitation(
        state=CoachInvitationState.SUPERSEDED.value,
        superseded_at=now,
        superseded_by_id=new_uuid(),
        expires_at=now - timedelta(days=1),
    )
    assert CoachInvitationService.presented_state(invitation, now=now) == "superseded"


def test_expired_outranks_blocked() -> None:
    now = utcnow()
    invitation = _invitation(
        expires_at=now - timedelta(seconds=1),
        blocked_at=now,
        blocked_reason=CoachInvitationBlockReason.ROLE_NOT_COACH.value,
    )
    assert CoachInvitationService.presented_state(invitation, now=now) == "expired"


def test_blocked_outranks_plain_awaiting() -> None:
    now = utcnow()
    invitation = _invitation(
        expires_at=now + timedelta(days=1),
        blocked_at=now,
        blocked_reason=CoachInvitationBlockReason.ALREADY_ASSIGNED.value,
    )
    assert CoachInvitationService.presented_state(invitation, now=now) == "blocked"


def test_plain_awaiting_is_the_default() -> None:
    now = utcnow()
    invitation = _invitation(expires_at=now + timedelta(days=1))
    assert CoachInvitationService.presented_state(invitation, now=now) == "awaiting"


def test_is_usable_ignores_blocked_at() -> None:
    """FR-015: a refused acceptance must not spend the invitation — a
    blocked-but-unexpired row stays usable."""
    now = utcnow()
    invitation = _invitation(
        expires_at=now + timedelta(days=1),
        blocked_at=now,
        blocked_reason=CoachInvitationBlockReason.ALREADY_ASSIGNED.value,
    )
    assert CoachInvitationRepository.is_usable(invitation, now=now) is True


def test_is_usable_false_once_expired_even_if_not_blocked() -> None:
    now = utcnow()
    invitation = _invitation(expires_at=now - timedelta(seconds=1))
    assert CoachInvitationRepository.is_usable(invitation, now=now) is False


def test_is_usable_false_once_accepted() -> None:
    now = utcnow()
    invitation = _invitation(
        state=CoachInvitationState.ACCEPTED.value,
        accepted_by_user_id=new_uuid(),
        accepted_at=now,
        expires_at=now + timedelta(days=1),
    )
    assert CoachInvitationRepository.is_usable(invitation, now=now) is False


def test_is_usable_false_once_revoked() -> None:
    now = utcnow()
    invitation = _invitation(
        state=CoachInvitationState.REVOKED.value, revoked_at=now, expires_at=now + timedelta(days=1)
    )
    assert CoachInvitationRepository.is_usable(invitation, now=now) is False
