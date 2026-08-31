from dataclasses import dataclass
from datetime import datetime

from app.models.user import User


@dataclass(frozen=True)
class ImpersonationContext:
    """The live impersonation riding the current request's session
    (data-model.md §105/§106, research.md R2-14). Present on
    `Principal.impersonation` only while an impersonation is open and has
    not just been ended by `ImpersonationService.resolve_for_session`
    (research.md R2-19)."""

    id: str
    admin_user_id: str
    target_user_id: str
    target_status_at_start: str
    started_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class Principal:
    """The caller of the current request, resolved once by `get_principal`
    (research.md R2-14).

    `effective_user` is who every existing endpoint, role gate, and
    ownership check sees — the impersonated person while an impersonation
    is live, otherwise the same account as `real_user`. `get_current_user`
    is a one-line wrapper returning this field, so every pre-existing
    dependency and router signature is unchanged by this feature.

    `real_user` is the account that actually authenticated with the
    session cookie — always a Super Admin while `impersonation` is set,
    and the one identity the exit route (`DELETE /admin/impersonations/
    current`) is allowed to authorize on, per research.md R2-15.

    `impersonation` is `None` for an ordinary request.
    """

    effective_user: User
    real_user: User
    impersonation: ImpersonationContext | None
