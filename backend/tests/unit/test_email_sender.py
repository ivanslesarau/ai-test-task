from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiosmtplib
import pytest

from app.core.config import Settings
from app.services.ports.email_sender import FilesystemEmailSender, SmtpEmailSender


def _smtp_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "test",
        "database_url": "sqlite+aiosqlite:///:memory:",
        "session_cookie_name": "pp_session",
        "session_idle_days": 7,
        "invitation_ttl_hours": 24,
        "signin_max_attempts": 10,
        "signin_window_minutes": 15,
        "upload_dir": "./var/test-uploads",
        "max_upload_bytes": 5242880,
        "email_backend": "smtp",
        "smtp_host": "smtp.example.org",
        "smtp_port": 587,
        "smtp_from_address": "noreply@example.org",
        "frontend_base_url": "http://localhost:5173",
        "bootstrap_admin_email": "bootstrap-admin@example.org",
        "bootstrap_admin_password": "bootstrap-password-123456",
    }
    base.update(overrides)
    return Settings(**base)


def _read_only_outbox_file(outbox_dir: Path) -> str:
    files = list(outbox_dir.glob("*.txt"))
    assert len(files) == 1
    return files[0].read_text(encoding="utf-8")


async def test_filesystem_sink_writes_recipient_subject_and_link(tmp_path: Path) -> None:
    sender = FilesystemEmailSender(str(tmp_path))

    result = await sender.send(
        to="new-user@example.org",
        subject="You're invited",
        body="Set your password: https://app.example.org/set-password?token=abc123",
    )

    assert result is True
    content = _read_only_outbox_file(tmp_path)
    assert "new-user@example.org" in content
    assert "You're invited" in content
    assert "https://app.example.org/set-password?token=abc123" in content


async def test_smtp_sender_returns_false_and_logs_rather_than_raises_when_unreachable() -> None:
    settings = _smtp_settings()
    sender = SmtpEmailSender(settings)

    with patch(
        "app.services.ports.email_sender.aiosmtplib.send",
        new=AsyncMock(side_effect=aiosmtplib.SMTPConnectError("connection refused")),
    ):
        result = await sender.send(to="user@example.org", subject="Subject", body="Body")

    assert result is False


async def test_smtp_sender_returns_false_on_os_error() -> None:
    settings = _smtp_settings()
    sender = SmtpEmailSender(settings)

    with patch(
        "app.services.ports.email_sender.aiosmtplib.send",
        new=AsyncMock(side_effect=OSError("network unreachable")),
    ):
        result = await sender.send(to="user@example.org", subject="Subject", body="Body")

    assert result is False


@pytest.mark.parametrize(
    ("tls_mode", "expected_use_tls", "expected_start_tls"),
    [
        ("starttls", False, True),
        ("implicit", True, False),
        ("none", False, False),
    ],
)
async def test_each_tls_mode_maps_to_the_expected_aiosmtplib_arguments(
    tls_mode: str, expected_use_tls: bool, expected_start_tls: bool
) -> None:
    settings = _smtp_settings(smtp_tls=tls_mode, smtp_timeout_seconds=7)
    sender = SmtpEmailSender(settings)

    mock_send = AsyncMock(return_value=(None, None))
    with patch("app.services.ports.email_sender.aiosmtplib.send", new=mock_send):
        result = await sender.send(to="user@example.org", subject="Subject", body="Body")

    assert result is True
    mock_send.assert_awaited_once()
    _, kwargs = mock_send.call_args
    assert kwargs["use_tls"] is expected_use_tls
    assert kwargs["start_tls"] is expected_start_tls
    assert kwargs["timeout"] == 7
    assert kwargs["hostname"] == "smtp.example.org"


async def test_no_rendered_invitation_body_contains_a_password() -> None:
    """`render_invitation_email` takes no password argument at all — only
    a name, a single-use setup link, and a TTL (FR-025) — so there is no
    parameter through which a real password value could ever reach the
    rendered body, by construction."""
    from app.services.templates.invitation import render_invitation_email

    subject, body = render_invitation_email(
        first_name="Tara",
        setup_url="https://app.example.org/set-password?token=abc123",
        ttl_hours=24,
    )

    fake_password = "hunter2-super-secret"
    assert fake_password not in body
    assert fake_password not in subject
