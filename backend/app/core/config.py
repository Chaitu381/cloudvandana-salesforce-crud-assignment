from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Salesforce Object Manager"
    environment: str = "development"
    app_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173,http://localhost:8000"

    sf_auth_base_url: str = "https://login.salesforce.com"
    sf_client_id: str = ""
    sf_client_secret: str = ""
    sf_api_version: str = "v67.0"
    sf_scopes: str = "api refresh_token"

    session_secret: str = "development-only-change-me-please"
    session_cookie_name: str = "sf_session"
    oauth_cookie_name: str = "sf_oauth_tx"
    session_max_age_seconds: int = 43200
    oauth_max_age_seconds: int = 600
    cookie_secure: bool = False
    api_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("app_base_url", "frontend_url", "sf_auth_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("sf_api_version")
    @classmethod
    def normalize_api_version(cls, value: str) -> str:
        value = value.strip()
        return value if value.startswith("v") else f"v{value}"

    @property
    def callback_url(self) -> str:
        return f"{self.app_base_url}/api/auth/callback"

    @property
    def oauth_authorize_url(self) -> str:
        return f"{self.sf_auth_base_url}/services/oauth2/authorize"

    @property
    def oauth_token_url(self) -> str:
        return f"{self.sf_auth_base_url}/services/oauth2/token"

    @property
    def oauth_revoke_url(self) -> str:
        return f"{self.sf_auth_base_url}/services/oauth2/revoke"

    @property
    def is_salesforce_configured(self) -> bool:
        return bool(self.sf_client_id.strip())

    @property
    def origin_allowlist(self) -> set[str]:
        values = {v.strip().rstrip("/") for v in self.allowed_origins.split(",") if v.strip()}
        values.add(self.app_base_url)
        values.add(self.frontend_url)
        return values

    def validate_runtime_security(self) -> None:
        if self.environment.lower() == "production":
            if self.session_secret == "development-only-change-me-please" or len(self.session_secret) < 32:
                raise RuntimeError("SESSION_SECRET must be a unique value of at least 32 characters in production")
            if not self.cookie_secure:
                raise RuntimeError("COOKIE_SECURE must be true in production")
            for name, value in (("APP_BASE_URL", self.app_base_url), ("FRONTEND_URL", self.frontend_url)):
                parsed = urlparse(value)
                if parsed.scheme != "https":
                    raise RuntimeError(f"{name} must use https in production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime_security()
    return settings
