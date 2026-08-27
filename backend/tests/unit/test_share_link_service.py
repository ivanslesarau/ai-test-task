from datetime import timedelta

from app.db.base import new_uuid, utcnow
from app.models.enums import ShareLinkKind
from app.models.share_link import ShareLink
from app.repositories.share_link_repository import ShareLinkRepository


def _link(**overrides: object) -> ShareLink:
    defaults: dict[str, object] = dict(
        id=new_uuid(),
        code="a" * 22,
        trainer_user_id=new_uuid(),
        created_by_user_id=new_uuid(),
        kind=ShareLinkKind.PLAYER_STANDING.value,
        target_email=None,
        expires_at=None,
        max_uses=None,
        use_count=0,
        is_active=True,
        revoked_at=None,
        created_at=utcnow(),
    )
    defaults.update(overrides)
    return ShareLink(**defaults)


def test_a_healthy_standing_link_is_usable() -> None:
    assert ShareLinkRepository.is_usable(_link()) is True


def test_an_inactive_link_is_not_usable() -> None:
    assert ShareLinkRepository.is_usable(_link(is_active=False)) is False


def test_a_revoked_link_is_not_usable_even_if_flagged_active() -> None:
    assert ShareLinkRepository.is_usable(_link(revoked_at=utcnow())) is False


def test_an_expired_link_is_not_usable() -> None:
    now = utcnow()
    assert (
        ShareLinkRepository.is_usable(_link(expires_at=now - timedelta(seconds=1)), now=now)
        is False
    )


def test_a_link_not_yet_expired_is_usable() -> None:
    now = utcnow()
    assert ShareLinkRepository.is_usable(_link(expires_at=now + timedelta(days=1)), now=now) is True


def test_an_exhausted_link_is_not_usable() -> None:
    assert ShareLinkRepository.is_usable(_link(max_uses=5, use_count=5)) is False


def test_a_link_under_its_max_uses_is_usable() -> None:
    assert ShareLinkRepository.is_usable(_link(max_uses=5, use_count=4)) is True


def test_a_standing_link_has_no_expiry_or_use_cap_by_construction() -> None:
    """FR-065: the standing player link this feature issues is unlimited
    and never expires — both fields are None for every link
    ShareLinkService.issue_standing_link creates."""
    link = _link()
    assert link.expires_at is None
    assert link.max_uses is None
