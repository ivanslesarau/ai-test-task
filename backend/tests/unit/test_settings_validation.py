import pytest
from pydantic import ValidationError

from app.core.config import Settings

# Every environment variable the `Settings` model can read that these tests
# rely on being *absent*. `backend/.env` (an ambient, developer-specific
# file — never committed with real values, but present on some machines
# with a real SMTP relay configured) and a developer's own exported shell
# variables can otherwise silently supply these, which would make a test
# that omits a key from its kwargs unable to prove the validator rejects
# its absence (see specs/001-user-roles-admin bug report, Defect 2).
_ENV_KEYS_UNDER_TEST = (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM_ADDRESS",
    "SMTP_TLS",
    "SMTP_TIMEOUT_SECONDS",
    "EMAIL_OUTBOX_DIR",
)


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


def _isolated_settings(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> Settings:
    """Construct `Settings` isolated from the ambient `.env` file and from
    any of these keys a developer's own shell might export — kwargs passed
    here are the *only* source for them, so a test that omits a key proves
    the validator actually rejects its absence rather than reading a value
    that happened to be lying around in the environment."""
    for key in _ENV_KEYS_UNDER_TEST:
        monkeypatch.delenv(key, raising=False)
    return Settings(_env_file=None, **_base_kwargs(**overrides))  # type: ignore[call-arg]


def test_filesystem_backend_constructs_without_any_smtp_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolated_settings(monkeypatch, email_backend="filesystem")


def test_smtp_backend_without_smtp_host_fails_to_construct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValidationError, match="SMTP_HOST"):
        _isolated_settings(
            monkeypatch,
            email_backend="smtp",
            smtp_from_address="noreply@example.org",
        )


def test_smtp_backend_without_smtp_from_address_fails_to_construct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValidationError, match="SMTP_FROM_ADDRESS"):
        _isolated_settings(
            monkeypatch,
            email_backend="smtp",
            smtp_host="smtp.example.org",
        )


def test_smtp_backend_with_both_required_keys_constructs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolated_settings(
        monkeypatch,
        email_backend="smtp",
        smtp_host="smtp.example.org",
        smtp_from_address="noreply@example.org",
    )


def test_smtp_tls_and_timeout_default_sensibly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _isolated_settings(monkeypatch, email_backend="filesystem")
    assert settings.smtp_tls == "starttls"
    assert settings.smtp_timeout_seconds == 10
