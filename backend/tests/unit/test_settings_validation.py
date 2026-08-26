import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _base_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "app_env": "test",
        "database_url": "sqlite+aiosqlite:///:memory:",
        "session_cookie_name": "pp_session",
        "session_idle_days": 7,
        "invitation_ttl_hours": 24,
        "signin_max_attempts": 10,
        "signin_window_minutes": 15,
        "upload_dir": "./var/test-uploads",
        "max_upload_bytes": 5242880,
        "email_backend": "filesystem",
        "frontend_base_url": "http://localhost:5173",
        "bootstrap_admin_email": "bootstrap-admin@example.org",
        "bootstrap_admin_password": "bootstrap-password-123456",
    }
    kwargs.update(overrides)
    return kwargs


def test_filesystem_backend_constructs_without_any_smtp_key() -> None:
    Settings(**_base_kwargs(email_backend="filesystem"))


def test_smtp_backend_without_smtp_host_fails_to_construct() -> None:
    with pytest.raises(ValidationError, match="SMTP_HOST"):
        Settings(**_base_kwargs(email_backend="smtp", smtp_from_address="noreply@example.org"))


def test_smtp_backend_without_smtp_from_address_fails_to_construct() -> None:
    with pytest.raises(ValidationError, match="SMTP_FROM_ADDRESS"):
        Settings(**_base_kwargs(email_backend="smtp", smtp_host="smtp.example.org"))


def test_smtp_backend_with_both_required_keys_constructs() -> None:
    Settings(
        **_base_kwargs(
            email_backend="smtp",
            smtp_host="smtp.example.org",
            smtp_from_address="noreply@example.org",
        )
    )


def test_smtp_tls_and_timeout_default_sensibly() -> None:
    settings = Settings(**_base_kwargs(email_backend="filesystem"))
    assert settings.smtp_tls == "starttls"
    assert settings.smtp_timeout_seconds == 10
