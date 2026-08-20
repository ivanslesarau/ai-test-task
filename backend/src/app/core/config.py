from functools import lru_cache
from typing import Literal

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

    frontend_base_url: str

    bootstrap_admin_email: str
    bootstrap_admin_password: str

    @property
    def cookie_secure(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
