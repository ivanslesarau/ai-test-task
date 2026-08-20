from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import (
    AccountNotActive,
    InvalidCredentials,
    InvitationNotUsable,
    NotAuthenticated,
    ValidationFailure,
)
from app.core.password_policy import validate_password
from app.core.rate_limit import check_rate_limit
from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.db.base import utcnow
from app.models.enums import AccountStatus
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.sign_in_attempt_repository import SignInAttemptRepository
from app.repositories.user_repository import UserRepository


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    visible = local[:1] or "*"
    return f"{visible}**@{domain}"


class AuthService:
    """Sign-in, session lifecycle, and rate limiting (US1).

    Password-setup methods for invited accounts (US2) are added to this
    same class in a later phase — see plan.md's Same-File Serialization
    note; both halves share this one service because they operate on the
    same session/credential concepts.
    """

    def __init__(self, db_session: AsyncSession, settings: Settings) -> None:
        self._settings = settings
        self._users = UserRepository(db_session)
        self._sessions = SessionRepository(db_session)
        self._attempts = SignInAttemptRepository(db_session)
        self._audit = AuditRepository(db_session)
        self._invitations = InvitationRepository(db_session)

    async def sign_in(self, *, email: str, password: str, client_ip: str) -> tuple[User, str]:
        """Returns the authenticated user and the raw session token (the
        caller sets it as the cookie value; only its hash is persisted)."""
        recent_failures = await self._attempts.count_recent_failures(
            email=email,
            client_ip=client_ip,
            window_minutes=self._settings.signin_window_minutes,
        )
        check_rate_limit(
            recent_failure_count=recent_failures,
            max_attempts=self._settings.signin_max_attempts,
            window_minutes=self._settings.signin_window_minutes,
        )

        user = await self._users.get_by_email(email)
        if (
            user is None
            or user.password_hash is None
            or not verify_password(password, user.password_hash)
        ):
            await self._attempts.record(email=email, client_ip=client_ip, successful=False)
            # FR-010: identical for unknown email, wrong password, and no
            # password set yet — none of these may be distinguishable.
            raise InvalidCredentials("Email or password is incorrect.")

        if user.status_enum is not AccountStatus.ACTIVE:
            await self._attempts.record(email=email, client_ip=client_ip, successful=False)
            raise AccountNotActive("Account deactivated. Contact support.")

        await self._attempts.record(email=email, client_ip=client_ip, successful=True)
        user.last_login_at = utcnow()

        raw_token = generate_token()
        await self._sessions.create(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            idle_days=self._settings.session_idle_days,
        )
        return user, raw_token

    async def authenticate_session(self, raw_token: str) -> User:
        """Validates a session cookie value and advances its sliding
        expiry (FR-011). Raises NotAuthenticated for any invalid, expired,
        revoked session, or one whose account is no longer Active
        (FR-018)."""
        record = await self._sessions.find_active_by_token_hash(hash_token(raw_token))
        if record is None or not SessionRepository.is_usable(record):
            raise NotAuthenticated("Sign in to continue.")

        user = await self._users.get_by_id(record.user_id)
        if user is None or user.status_enum is not AccountStatus.ACTIVE:
            raise NotAuthenticated("Sign in to continue.")

        await self._sessions.touch(record, idle_days=self._settings.session_idle_days)
        return user

    async def sign_out(self, raw_token: str) -> None:
        record = await self._sessions.find_active_by_token_hash(hash_token(raw_token))
        if record is not None:
            await self._sessions.revoke(record)

    async def check_invitation(self, raw_token: str) -> tuple[str, datetime]:
        """Returns (masked email hint, expiry) for a usable invitation, so
        the set-password page can show "this link has expired" before the
        person types a password (FR-027)."""
        invitation = await self._invitations.find_by_token_hash(hash_token(raw_token))
        if invitation is None or not InvitationRepository.is_usable(invitation):
            raise InvitationNotUsable("This setup link is no longer valid. Request a new one.")

        user = await self._users.get_by_id(invitation.user_id)
        if user is None or user.status_enum is not AccountStatus.ACTIVE:
            raise InvitationNotUsable("This setup link is no longer valid. Request a new one.")

        return _mask_email(user.email), invitation.expires_at

    async def setup_password(self, raw_token: str, password: str) -> None:
        """Sets the first password for an invited account and consumes
        the invitation (FR-026, FR-027)."""
        invitation = await self._invitations.find_by_token_hash(hash_token(raw_token))
        if invitation is None or not InvitationRepository.is_usable(invitation):
            raise InvitationNotUsable("This setup link is no longer valid. Request a new one.")

        user = await self._users.get_by_id(invitation.user_id)
        if user is None or user.status_enum is not AccountStatus.ACTIVE:
            raise InvitationNotUsable("This setup link is no longer valid. Request a new one.")

        policy_error = validate_password(password)
        if policy_error:
            raise ValidationFailure(
                "One or more fields are invalid.", fields={"password": policy_error}
            )

        user.password_hash = hash_password(password)
        await self._invitations.consume(invitation)
        await self._audit.add(
            action="invitation_consumed",
            actor_user_id=user.id,
            target_user_id=user.id,
        )

    async def record_permission_denied(self, *, actor_user_id: str | None, detail: str) -> None:
        """FR-020: every refused cross-boundary attempt is recorded."""
        await self._audit.add(
            action="permission_denied",
            actor_user_id=actor_user_id,
            target_user_id=None,
            detail=detail,
        )
