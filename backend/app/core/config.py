"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for Industrial Brain AI.

    Values are read from environment variables (and optional `.env` files).
    Production mode fails fast when critical secrets still use placeholder defaults.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_env: Literal["development", "production", "test"] = "development"
    app_name: str = "Industrial Brain AI"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    api_prefix: str = "/api/v1"

    # --- PostgreSQL ---
    database_url: str = (
        "postgresql+psycopg://industrial_brain:change-me@localhost:5432/industrial_brain"
    )

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # --- Auth ---
    auth_provider: str = "jwt"
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # --- Optional integrations (wired in later milestones) ---
    openai_api_key: str = ""
    google_api_key: str = ""
    anthropic_api_key: str = ""

    debug: bool = Field(default=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _normalize_cors_origins(cls, value: object) -> object:
        if isinstance(value, list):
            return ",".join(str(item).strip() for item in value if str(item).strip())
        return value

    @model_validator(mode="after")
    def _fail_fast_in_production(self) -> Settings:
        if self.app_env != "production":
            return self

        insecure_secrets: list[str] = []
        if not self.jwt_secret or self.jwt_secret.startswith("change-me"):
            insecure_secrets.append("JWT_SECRET")
        if "change-me" in self.database_url:
            insecure_secrets.append("DATABASE_URL")

        if insecure_secrets:
            joined = ", ".join(insecure_secrets)
            raise ValueError(
                f"Production mode requires non-placeholder values for: {joined}"
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = self.cors_origins.split(",")
        return [origin.strip() for origin in origins if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton used by Depends and app factory."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear settings cache (tests / runtime env reloads)."""
    get_settings.cache_clear()
