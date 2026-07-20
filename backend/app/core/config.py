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
    jwt_refresh_token_expire_days: int = 7

    # --- Object storage (Azure Blob / MinIO / local) ---
    storage_backend: Literal["local", "minio", "s3", "azure"] = "local"
    storage_endpoint: str = "localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "industrial-brain"
    storage_use_ssl: bool = False
    storage_region: str = "us-east-1"
    storage_local_root: str = ".data/storage"
    storage_max_upload_bytes: int = 100 * 1024 * 1024
    # Comma-separated; empty → built-in industrial MIME allow-list
    storage_allowed_mime_types: str = ""
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "industrial-brain"

    # --- Corpus source (Milestone 1.6 — local primary; Drive optional later) ---
    corpus_source: Literal["local", "gdrive"] = "local"
    corpus_local_root: str = ""
    corpus_discovery_batch_size: int = 500
    corpus_download_max_files: int = 50
    corpus_download_max_bytes: int = 500 * 1024 * 1024
    google_drive_folder_id: str = ""
    google_service_account_file: str = ""

    # --- Optional integrations (wired in later milestones) ---
    openai_api_key: str = ""
    google_api_key: str = ""
    anthropic_api_key: str = ""

    # --- Azure Document Intelligence (Milestone 2.1 — T1) ---
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""
    # When Azure DI is unset, demote T1 → T2 (PyMuPDF) instead of failing hard
    parse_fallback_without_azure: bool = True

    # --- Embeddings (Milestone 2.4) ---
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # --- Qdrant (Milestone 2.5) ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "industrial_brain_chunks"

    # --- Neo4j (Milestone 2.6) ---
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "change-me-neo4j"

    # --- Logging / observability (Milestone 1.10) ---
    log_level: str = "INFO"
    log_json: bool = True

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

    @property
    def storage_allowed_mime_types_set(self) -> frozenset[str]:
        raw = self.storage_allowed_mime_types.strip()
        if not raw:
            return frozenset()
        return frozenset(
            part.strip().lower() for part in raw.split(",") if part.strip()
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton used by Depends and app factory."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear settings cache (tests / runtime env reloads)."""
    get_settings.cache_clear()
