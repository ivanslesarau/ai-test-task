from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.share_link import ShareLink as ShareLinkModel


class ShareLinkOut(BaseModel):
    """Matches contracts/openapi.yaml `ShareLink`. `code` is returned in
    clear — it is stored in clear (data-model.md §16, research.md R-21)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    code: str
    url: str
    kind: str
    is_active: bool
    use_count: int
    expires_at: datetime | None
    max_uses: int | None
    created_at: datetime


def build_share_link_out(link: ShareLinkModel, *, frontend_base_url: str) -> ShareLinkOut:
    return ShareLinkOut(
        id=link.id,
        code=link.code,
        url=f"{frontend_base_url}/join/{link.code}",
        kind=link.kind,
        is_active=link.is_active,
        use_count=link.use_count,
        expires_at=link.expires_at,
        max_uses=link.max_uses,
        created_at=link.created_at,
    )
