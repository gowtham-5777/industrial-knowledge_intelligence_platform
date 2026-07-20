"""Qdrant vector index client (Milestone 2.5)."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ErrorCode
from app.observability import get_logger

_logger = get_logger(__name__)


class QdrantIndex:
    """Collection schema + upsert / delete / filtered search."""

    def __init__(
        self, settings: Settings | None = None, *, client: Any | None = None
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client
        self.collection = self.settings.qdrant_collection
        self.dimensions = int(self.settings.embedding_dimensions)

    def ensure_collection(self) -> None:
        client = self._get_client()
        from qdrant_client.http import models as qm

        names = {c.name for c in client.get_collections().collections}
        if self.collection in names:
            return
        client.create_collection(
            collection_name=self.collection,
            vectors_config=qm.VectorParams(
                size=self.dimensions,
                distance=qm.Distance.COSINE,
            ),
        )
        # Payload indexes for Architecture filters
        for field in ("document_id", "doc_category", "asset_id"):
            client.create_payload_index(
                collection_name=self.collection,
                field_name=field,
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )
        # drawing_numbers / motor_models are arrays — keyword still works for match
        for field in ("drawing_numbers", "motor_models"):
            try:
                client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field,
                    field_schema=qm.PayloadSchemaType.KEYWORD,
                )
            except Exception:  # noqa: BLE001 — index may already exist / unsupported
                _logger.warning("qdrant payload index skipped", extra={"field": field})
        _logger.info("qdrant collection ready", extra={"collection": self.collection})

    def upsert_points(self, points: list[dict[str, Any]]) -> int:
        if not points:
            return 0
        self.ensure_collection()
        from qdrant_client.http import models as qm

        client = self._get_client()
        qpoints = [
            qm.PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p.get("payload") or {},
            )
            for p in points
        ]
        client.upsert(collection_name=self.collection, points=qpoints)
        return len(qpoints)

    def delete_by_document(self, document_id: str) -> None:
        self.ensure_collection()
        from qdrant_client.http import models as qm

        client = self._get_client()
        client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="document_id",
                            match=qm.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )

    def search(
        self,
        vector: list[float],
        *,
        limit: int = 8,
        document_id: str | None = None,
        doc_category: str | None = None,
        drawing_number: str | None = None,
        motor_model: str | None = None,
        asset_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_collection()
        from qdrant_client.http import models as qm

        must: list[Any] = []
        if document_id:
            must.append(
                qm.FieldCondition(
                    key="document_id", match=qm.MatchValue(value=document_id)
                )
            )
        if doc_category:
            must.append(
                qm.FieldCondition(
                    key="doc_category", match=qm.MatchValue(value=doc_category)
                )
            )
        if asset_id:
            must.append(
                qm.FieldCondition(key="asset_id", match=qm.MatchValue(value=asset_id))
            )
        if drawing_number:
            must.append(
                qm.FieldCondition(
                    key="drawing_numbers", match=qm.MatchValue(value=drawing_number)
                )
            )
        if motor_model:
            must.append(
                qm.FieldCondition(
                    key="motor_models", match=qm.MatchValue(value=motor_model)
                )
            )

        query_filter = qm.Filter(must=must) if must else None
        client = self._get_client()
        hits = client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return [
            {
                "id": str(hit.id),
                "score": float(hit.score),
                "payload": dict(hit.payload or {}),
            }
            for hit in hits
        ]

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:  # pragma: no cover
            raise AppError(
                "qdrant-client is not installed",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
            ) from exc
        url = (self.settings.qdrant_url or "").strip()
        if not url:
            raise AppError(
                "QDRANT_URL is not configured",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
            )
        api_key = (self.settings.qdrant_api_key or "").strip() or None
        self._client = QdrantClient(
            url=url,
            api_key=api_key,
            prefer_grpc=False,
            check_compatibility=False,
        )
        return self._client


class InMemoryQdrantIndex:
    """Test double for Qdrant when the service is unavailable."""

    def __init__(self, dimensions: int = 32) -> None:
        self.dimensions = dimensions
        self.collection = "memory"
        self._points: dict[str, dict[str, Any]] = {}

    def ensure_collection(self) -> None:
        return None

    def upsert_points(self, points: list[dict[str, Any]]) -> int:
        for p in points:
            self._points[str(p["id"])] = p
        return len(points)

    def delete_by_document(self, document_id: str) -> None:
        drop = [
            pid
            for pid, p in self._points.items()
            if (p.get("payload") or {}).get("document_id") == document_id
        ]
        for pid in drop:
            del self._points[pid]

    def search(
        self,
        vector: list[float],
        *,
        limit: int = 8,
        document_id: str | None = None,
        doc_category: str | None = None,
        drawing_number: str | None = None,
        motor_model: str | None = None,
        asset_id: str | None = None,
    ) -> list[dict[str, Any]]:
        scored: list[tuple[float, dict[str, Any]]] = []
        for pid, p in self._points.items():
            payload = p.get("payload") or {}
            if document_id and payload.get("document_id") != document_id:
                continue
            if doc_category and payload.get("doc_category") != doc_category:
                continue
            if asset_id and payload.get("asset_id") != asset_id:
                continue
            if drawing_number and drawing_number not in (
                payload.get("drawing_numbers") or []
            ):
                continue
            if motor_model and motor_model not in (payload.get("motor_models") or []):
                continue
            vec = p.get("vector") or []
            score = _cosine(vector, vec)
            scored.append((score, {"id": pid, "score": score, "payload": payload}))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
