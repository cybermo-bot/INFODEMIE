"""Application settings, read from the environment and the repository `.env`.

Core settings are validated at startup and stop the app when wrong. Optional
integration keys never crash the app: a missing key marks the related
integration "non configuré" (see `integration_status`).
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
INSECURE_SECRET_KEYS = {"", "change-me"}


class AppEnv(StrEnum):
    DEV = "dev"
    TEST = "test"
    DEMO = "demo"
    PILOT = "pilot"


class AIMode(StrEnum):
    HYBRID = "hybrid"
    LOCAL = "local"


class IntegrationState(StrEnum):
    CONFIGURED = "configure"
    NOT_CONFIGURED = "non_configure"
    DISABLED = "desactive"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # An empty value in .env (KEY=) means "not set".
        env_parse_none_str="",
    )

    # Core
    app_env: AppEnv = AppEnv.DEV
    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    default_locale: str = "fr"
    default_timezone: str = "Africa/Tunis"
    database_url: str = "postgresql+psycopg://pnsi:pnsi@localhost:5433/pnsi"
    test_database_url: str = "postgresql+psycopg://pnsi:pnsi@localhost:5433/pnsi_test"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: SecretStr = SecretStr("change-me")
    data_dir: Path = REPO_ROOT / "data"
    log_level: str = "INFO"

    # Sessions (decision D13)
    session_idle_hours: int = Field(default=12, ge=1, le=72)
    session_max_hours: int = Field(default=168, ge=1, le=720)
    cookie_secure: bool | None = None  # defaults to True outside dev and test

    # AI (decision D5)
    ai_mode: AIMode = AIMode.HYBRID
    external_ai_enabled: bool = True
    gemini_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "bge-m3"
    local_chat_model: str = "qwen3:4b-instruct"
    ai_daily_budget_gemini_requests: int | None = None
    ai_daily_budget_groq_requests: int | None = None

    # Google
    google_api_key: SecretStr | None = None
    youtube_daily_unit_budget: int = 9000

    # Telegram
    telegram_api_id: str | None = None
    telegram_api_hash: SecretStr | None = None
    telegram_phone: SecretStr | None = None
    telegram_bot_token: SecretStr | None = None

    # Social routes (decision D4)
    apify_token: SecretStr | None = None
    apify_max_spend_usd: float = 5
    facebook_page_tokens: SecretStr | None = None
    meta_app_id: str | None = None
    meta_app_secret: SecretStr | None = None

    # Optional sources
    bluesky_base_url: str = "https://public.api.bsky.app"
    reddit_client_id: str | None = None
    reddit_client_secret: SecretStr | None = None
    reddit_user_agent: str = "pnsi/0.1 (public health monitoring)"

    # Evidence discovery
    ncbi_email: str | None = None
    ncbi_api_key: SecretStr | None = None
    ncbi_tool: str = "pnsi"

    # Governance
    auto_publish_enabled: bool = False
    raw_retention_hours: int = 24
    redacted_retention_days: int = 90

    # Email
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    alert_from: str = "pnsi@localhost"

    @field_validator("default_locale")
    @classmethod
    def _locale_supported(cls, value: str) -> str:
        if value not in {"fr", "ar", "en"}:
            raise ValueError("DEFAULT_LOCALE must be fr, ar or en")
        return value

    @field_validator("data_dir", mode="before")
    @classmethod
    def _data_dir_from_repo_root(cls, value: object) -> Path:
        # Commands run from apps/api, so relative paths are anchored at the repo root.
        if value in (None, ""):
            return REPO_ROOT / "data"
        path = Path(str(value)).expanduser()
        return path if path.is_absolute() else (REPO_ROOT / path).resolve()

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _postgres_only(cls, value: str) -> str:
        if not value.startswith("postgresql"):
            raise ValueError("PNSI needs PostgreSQL (postgresql+psycopg://...)")
        return value

    @model_validator(mode="after")
    def _guard_production_values(self) -> Settings:
        if self.app_env not in (AppEnv.DEV, AppEnv.TEST):
            if self.secret_key.get_secret_value() in INSECURE_SECRET_KEYS:
                raise ValueError("SECRET_KEY must be set to a random value outside dev and test")
            if len(self.secret_key.get_secret_value()) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters outside dev and test")
        if self.auto_publish_enabled:
            # Rule 8: humans publish. There is no publishing integration to enable.
            raise ValueError("AUTO_PUBLISH_ENABLED must stay false: PNSI never publishes itself")
        return self

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.app_env not in (AppEnv.DEV, AppEnv.TEST)

    @property
    def is_dev(self) -> bool:
        return self.app_env in (AppEnv.DEV, AppEnv.TEST)

    def secret_values(self) -> list[str]:
        """Every non-empty secret value, used by the log redactor."""
        values = []
        for name in type(self).model_fields:
            value = getattr(self, name)
            if isinstance(value, SecretStr):
                raw = value.get_secret_value()
                if raw and raw not in INSECURE_SECRET_KEYS:
                    values.append(raw)
        return values

    def integration_status(self) -> dict[str, IntegrationState]:
        """State of each optional integration, derived from configured keys only."""

        def has(*values: object) -> IntegrationState:
            ok = all(
                (v.get_secret_value() if isinstance(v, SecretStr) else v) not in (None, "")
                for v in values
            )
            return IntegrationState.CONFIGURED if ok else IntegrationState.NOT_CONFIGURED

        hosted_ai = self.ai_mode == AIMode.HYBRID and self.external_ai_enabled
        status = {
            "gemini": has(self.gemini_api_key) if hosted_ai else IntegrationState.DISABLED,
            "groq": has(self.groq_api_key) if hosted_ai else IntegrationState.DISABLED,
            "ollama": has(self.ollama_base_url),
            "youtube": has(self.google_api_key),
            "fact_check_tools": has(self.google_api_key),
            "telegram_client": has(self.telegram_api_id, self.telegram_api_hash),
            "telegram_bot": has(self.telegram_bot_token),
            "apify": has(self.apify_token),
            "facebook_pages": has(self.facebook_page_tokens),
            "meta_app": has(self.meta_app_id, self.meta_app_secret),
            "reddit": has(self.reddit_client_id, self.reddit_client_secret),
            "ncbi": has(self.ncbi_email),
            "smtp": has(self.smtp_host),
        }
        return status


@lru_cache
def get_settings() -> Settings:
    return Settings()
