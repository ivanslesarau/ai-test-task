from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every configurable value, loaded from the environment.

    No field has a default that would be wrong in production — startup fails
    on a missing required value rather than silently falling back
    (constitution: configuration via pydantic-settings).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"]

    database_url: str

    session_cookie_name: str
    session_idle_days: int

    invitation_ttl_hours: int

    signin_max_attempts: int
    signin_window_minutes: int

    upload_dir: str
    max_upload_bytes: int

    email_backend: Literal["filesystem", "smtp"]
    email_outbox_dir: str = "./var/outbox"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str | None = None
    # STARTTLS (587) is the common case; "implicit" reaches a relay on 465
    # and "none" reaches a local dev sink like Mailpit/MailHog on 1025 —
    # the previous hard-coded `start_tls=True` could reach none of those.
    smtp_tls: Literal["starttls", "implicit", "none"] = "starttls"
    smtp_timeout_seconds: int = 10

    frontend_base_url: str

    bootstrap_admin_email: str
    bootstrap_admin_password: str

    @property
    def cookie_secure(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _smtp_settings_required_when_backend_is_smtp(self) -> "Settings":
        # A misconfigured relay must fail at startup, not turn every
        # invitation into a swallowed exception and a silent
        # `invitation_sent: false` (T187).
        if self.email_backend == "smtp":
            missing = [
                name
                for name, value in (
                    ("SMTP_HOST", self.smtp_host),
                    ("SMTP_FROM_ADDRESS", self.smtp_from_address),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    "EMAIL_BACKEND=smtp requires the following settings: " + ", ".join(missing)
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
