"""Embedding provider abstraction (Milestone 2.4)."""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ErrorCode
from app.observability import get_logger

_logger = get_logger(__name__)


class EmbeddingProvider(Protocol):
    model_name: str
    model_version: str
    dimensions: int
    provider: str

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingProvider:
    """Hackathon embedding provider — text-embedding-3-small (1536-d)."""

    provider = "openai"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        model_name: str | None = None,
        client: object | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self.model_name = model_name or self._settings.embedding_model
        self.dimensions = int(self._settings.embedding_dimensions)
        self.model_version = f"{self.provider}:{self.model_name}"
        self._client = client

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        # OpenAI embeddings API — batch in chunks of 64
        vectors: list[list[float]] = []
        batch_size = 64
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = client.embeddings.create(
                model=self.model_name,
                input=batch,
            )
            # Ensure order by index
            ordered = sorted(response.data, key=lambda d: d.index)
            vectors.extend([list(item.embedding) for item in ordered])
        _logger.info(
            "openai embeddings created",
            extra={"count": len(texts), "model": self.model_name},
        )
        return vectors

    def _get_client(self):
        if self._client is not None:
            return self._client
        api_key = (self._settings.openai_api_key or "").strip()
        if not api_key:
            raise AppError(
                "OPENAI_API_KEY is not configured",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise AppError(
                "openai package is not installed",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
            ) from exc
        self._client = OpenAI(api_key=api_key)
        return self._client


class HashEmbeddingProvider:
    """Deterministic local embedder for unit tests (no API calls)."""

    provider = "hash"
    model_name = "hash-embed-v1"
    model_version = "hash:hash-embed-v1"
    dimensions = 32

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dimensions
            for i, ch in enumerate(text.encode("utf-8")):
                vec[i % self.dimensions] += (ch % 31) / 31.0
            # L2 normalize
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            out.append([v / norm for v in vec])
        return out


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    cfg = settings or get_settings()
    if cfg.app_env == "test":
        return HashEmbeddingProvider()
    return OpenAIEmbeddingProvider(cfg)
