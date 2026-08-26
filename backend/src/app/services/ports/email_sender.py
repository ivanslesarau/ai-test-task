import logging
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

import aiosmtplib

from app.core.config import Settings
from app.db.base import new_uuid, utcnow

logger = logging.getLogger("app.email")


class EmailSender(Protocol):
    async def send(self, *, to: str, subject: str, body: str) -> bool:
        """Returns True if the message was accepted for delivery."""
        ...


class FilesystemEmailSender:
    """Development/test sink: writes each message to a file instead of
    sending it, so tests and local development need no mail server
    (research.md R-11)."""

    def __init__(self, outbox_dir: str) -> None:
        self._outbox_dir = Path(outbox_dir)

    async def send(self, *, to: str, subject: str, body: str) -> bool:
        self._outbox_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{utcnow().strftime('%Y%m%d%H%M%S')}-{new_uuid()}.txt"
        (self._outbox_dir / filename).write_text(
            f"To: {to}\nSubject: {subject}\n\n{body}", encoding="utf-8"
        )
        return True


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send(self, *, to: str, subject: str, body: str) -> bool:
        message = EmailMessage()
        # No fallback here: `Settings` itself now refuses to start with
        # EMAIL_BACKEND=smtp unless SMTP_FROM_ADDRESS is set (T187), so a
        # hard-coded production default would only ever mask that guard.
        message["From"] = self._settings.smtp_from_address
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        # start_tls=True/False and use_tls map the three configured
        # modes: STARTTLS (587), implicit TLS (465), and no TLS at all
        # (a local dev sink like Mailpit/MailHog on 1025).
        use_tls = self._settings.smtp_tls == "implicit"
        start_tls = self._settings.smtp_tls == "starttls"

        try:
            await aiosmtplib.send(
                message,
                hostname=self._settings.smtp_host,
                port=self._settings.smtp_port,
                username=self._settings.smtp_username,
                password=self._settings.smtp_password,
                use_tls=use_tls,
                start_tls=start_tls,
                timeout=self._settings.smtp_timeout_seconds,
            )
            return True
        except (aiosmtplib.SMTPException, OSError):
            logger.exception("Failed to send email to %s", to)
            return False


def get_email_sender(settings: Settings) -> EmailSender:
    if settings.email_backend == "smtp":
        return SmtpEmailSender(settings)
    return FilesystemEmailSender(settings.email_outbox_dir)
