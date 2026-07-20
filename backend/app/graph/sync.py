"""Neo4j knowledge graph sync (Milestone 2.6)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.db.models.documents import Document
from app.db.models.extraction import TestMeasurement
from app.db.models.motors import MotorModel
from app.observability import get_logger

_logger = get_logger(__name__)

CONSTRAINT_STATEMENTS = [
    (
        "CREATE CONSTRAINT motor_model_code IF NOT EXISTS "
        "FOR (m:MotorModel) REQUIRE m.code IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT drawing_number_code IF NOT EXISTS "
        "FOR (d:DrawingNumber) REQUIRE d.code IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT document_id IF NOT EXISTS "
        "FOR (doc:Document) REQUIRE doc.id IS UNIQUE"
    ),
    (
        "CREATE INDEX document_category IF NOT EXISTS "
        "FOR (doc:Document) ON (doc.doc_category)"
    ),
]


class Neo4jGraphClient:
    """Thin Neo4j driver wrapper."""

    def __init__(
        self, settings: Settings | None = None, *, driver: Any | None = None
    ) -> None:
        self.settings = settings or get_settings()
        self._driver = driver

    def ensure_schema(self) -> None:
        with self._session() as session:
            for stmt in CONSTRAINT_STATEMENTS:
                try:
                    session.run(stmt)
                except Exception as exc:  # noqa: BLE001
                    _logger.warning(
                        "neo4j constraint skipped",
                        extra={"error": str(exc), "stmt": stmt[:48]},
                    )

    def run(
        self, cypher: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        with self._session() as session:
            result = session.run(cypher, parameters or {})
            return [dict(record) for record in result]

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def _session(self):
        driver = self._get_driver()
        return driver.session()

    def _get_driver(self):
        if self._driver is not None:
            return self._driver
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:  # pragma: no cover
            raise AppError(
                "neo4j package is not installed",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
            ) from exc
        uri = (self.settings.neo4j_uri or "").strip()
        if not uri:
            raise AppError(
                "NEO4J_URI is not configured",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
            )
        self._driver = GraphDatabase.driver(
            uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )
        return self._driver


class InMemoryGraphStore:
    """Test double storing motor-centered edges."""

    def __init__(self) -> None:
        self.motors: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, dict[str, Any]] = {}
        self.drawings: dict[str, dict[str, Any]] = {}
        self.edges: list[tuple[str, str, str, dict[str, Any]]] = []

    def ensure_schema(self) -> None:
        return None

    def run(
        self, cypher: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        # Minimal support for neighborhood query used in retrieval
        params = parameters or {}
        if "MotorModel" in cypher and "code" in params:
            code = params["code"]
            motor = self.motors.get(code)
            if not motor:
                return []
            linked = []
            for rel, src, dst, _meta in self.edges:
                if src == f"motor:{code}" and dst.startswith("doc:"):
                    doc_id = dst.split(":", 1)[1]
                    linked.append({"doc": self.documents.get(doc_id), "rel": rel})
            return [{"motor": motor, "links": linked}]
        return []

    def merge_motor(self, code: str, props: dict[str, Any]) -> None:
        self.motors[code] = {**props, "code": code}

    def merge_document(self, doc_id: str, props: dict[str, Any]) -> None:
        self.documents[doc_id] = {**props, "id": doc_id}

    def merge_drawing(self, code: str, props: dict[str, Any]) -> None:
        self.drawings[code] = {**props, "code": code}

    def merge_edge(
        self, rel: str, src: str, dst: str, props: dict[str, Any] | None = None
    ) -> None:
        key = (rel, src, dst)
        self.edges = [e for e in self.edges if (e[0], e[1], e[2]) != key]
        self.edges.append((rel, src, dst, props or {}))

    def close(self) -> None:
        return None


_HAS_REL_BY_CATEGORY: dict[str, str] = {
    "datasheet": "HAS_DATASHEET",
    "test_report": "HAS_TEST_REPORT",
    "checklist": "HAS_TEST_REPORT",
    "certificate": "HAS_CERTIFICATION",
    "manual": "HAS_MANUAL",
    "sop": "HAS_SOP",
    "drawing": "HAS_DRAWING",
    "drawing_dimension": "HAS_DRAWING",
    "drawing_outline": "HAS_DRAWING",
    "drawing_cad": "HAS_DRAWING",
    "drawing_shaft": "HAS_DRAWING",
    "drawing_connection": "HAS_DRAWING",
    "drawing_mechanical": "HAS_DRAWING",
    "drawing_terminal": "HAS_DRAWING",
    "regulation": "HAS_CERTIFICATION",
}


class GraphSyncService:
    """Project SoR documents / motors / drawings into Neo4j idempotently."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        client: Neo4jGraphClient | InMemoryGraphStore | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        if client is not None:
            self.client = client
        elif self.settings.app_env == "test":
            self.client = InMemoryGraphStore()
        else:
            try:
                self.client = Neo4jGraphClient(self.settings)
                self.client.ensure_schema()
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "neo4j unavailable; using in-memory graph",
                    extra={"error": str(exc)},
                )
                self.client = InMemoryGraphStore()

    def sync_document(self, document_id: str) -> dict[str, Any]:
        document = self._get_document(document_id)
        catalog = document.catalog_entry
        category = (
            catalog.doc_category
            if catalog and catalog.doc_category
            else document.doc_type
        ) or "document"
        motor_code = catalog.motor_type_code if catalog else None
        drawing_number = catalog.drawing_number if catalog else None

        # Ensure motor model stub in Postgres when code present
        if motor_code:
            self._ensure_motor_model(motor_code)

        props = {
            "id": document.id,
            "title": document.title,
            "doc_category": category,
            "status": document.status,
        }
        rel = _HAS_REL_BY_CATEGORY.get(category, "HAS_DOCUMENT")

        if isinstance(self.client, InMemoryGraphStore):
            self.client.merge_document(document.id, props)
            if motor_code:
                self.client.merge_motor(
                    motor_code, {"code": motor_code, "name": motor_code}
                )
                self.client.merge_edge(rel, f"motor:{motor_code}", f"doc:{document.id}")
            if drawing_number:
                self.client.merge_drawing(drawing_number, {"code": drawing_number})
                self.client.merge_edge(
                    "LINKED_VIA", f"doc:{document.id}", f"drawing:{drawing_number}"
                )
                if motor_code:
                    self.client.merge_edge(
                        "IDENTIFIED_BY",
                        f"motor:{motor_code}",
                        f"drawing:{drawing_number}",
                    )
        else:
            self.client.ensure_schema()
            self.client.run(
                """
                MERGE (doc:Document {id: $id})
                SET doc.title = $title,
                    doc.doc_category = $doc_category,
                    doc.status = $status
                """,
                props,
            )
            if motor_code:
                # Relationship type is from controlled CATEGORY map (not user input)
                cypher = (
                    "MERGE (m:MotorModel {code: $code}) "
                    "SET m.name = coalesce(m.name, $code) "
                    "WITH m "
                    "MATCH (doc:Document {id: $doc_id}) "
                    f"MERGE (m)-[r:{rel}]->(doc) "
                    "SET r.synced = true"
                )
                self.client.run(
                    cypher,
                    {"code": motor_code, "doc_id": document.id},
                )
            if drawing_number:
                self.client.run(
                    """
                    MERGE (d:DrawingNumber {code: $code})
                    WITH d
                    MATCH (doc:Document {id: $doc_id})
                    MERGE (doc)-[:LINKED_VIA]->(d)
                    """,
                    {"code": drawing_number, "doc_id": document.id},
                )
                if motor_code:
                    self.client.run(
                        """
                        MATCH (m:MotorModel {code: $motor})
                        MATCH (d:DrawingNumber {code: $drawing})
                        MERGE (m)-[:IDENTIFIED_BY]->(d)
                        """,
                        {"motor": motor_code, "drawing": drawing_number},
                    )

        # Attach measurements as HAS_MEASUREMENT from document
        measurements = list(
            self.session.scalars(
                select(TestMeasurement).where(
                    TestMeasurement.document_id == document.id
                )
            ).all()
        )
        for m in measurements:
            if isinstance(self.client, InMemoryGraphStore):
                self.client.merge_edge(
                    "HAS_MEASUREMENT",
                    f"doc:{document.id}",
                    f"meas:{m.id}",
                    {
                        "parameter": m.parameter,
                        "value": m.measured_value or m.rated_value,
                    },
                )
            else:
                self.client.run(
                    """
                    MATCH (doc:Document {id: $doc_id})
                    MERGE (t:TestMeasurement {id: $mid})
                    SET t.parameter = $parameter,
                        t.unit = $unit,
                        t.measured_value = $measured,
                        t.rated_value = $rated,
                        t.numeric_value = $numeric
                    MERGE (doc)-[:HAS_MEASUREMENT]->(t)
                    """,
                    {
                        "doc_id": document.id,
                        "mid": m.id,
                        "parameter": m.parameter,
                        "unit": m.unit,
                        "measured": m.measured_value,
                        "rated": m.rated_value,
                        "numeric": m.numeric_value,
                    },
                )

        _logger.info(
            "graph sync complete",
            extra={
                "document_id": document.id,
                "motor": motor_code,
                "drawing": drawing_number,
                "measurements": len(measurements),
            },
        )
        return {
            "document_id": document.id,
            "motor_type_code": motor_code,
            "drawing_number": drawing_number,
            "relationship": rel,
            "measurement_count": len(measurements),
        }

    def neighborhood(self, motor_code: str) -> dict[str, Any]:
        if isinstance(self.client, InMemoryGraphStore):
            rows = self.client.run(
                "MATCH (m:MotorModel {code: $code})", {"code": motor_code}
            )
            if not rows:
                return {"motor": None, "documents": []}
            links = rows[0].get("links") or []
            return {
                "motor": rows[0].get("motor"),
                "documents": [
                    {**(item.get("doc") or {}), "relationship": item.get("rel")}
                    for item in links
                ],
            }

        rows = self.client.run(
            """
            MATCH (m:MotorModel {code: $code})
            OPTIONAL MATCH (m)-[r]->(doc:Document)
            RETURN m AS motor, collect({doc: doc, rel: type(r)}) AS links
            """,
            {"code": motor_code},
        )
        if not rows:
            return {"motor": None, "documents": []}
        motor = rows[0].get("motor")
        links = rows[0].get("links") or []
        documents = []
        for item in links:
            doc = item.get("doc")
            if doc is None:
                continue
            documents.append({**dict(doc), "relationship": item.get("rel")})
        return {"motor": dict(motor) if motor else None, "documents": documents}

    def _ensure_motor_model(self, code: str) -> MotorModel | None:
        existing = self.session.scalars(
            select(MotorModel).where(MotorModel.code == code)
        ).first()
        if existing:
            return existing
        from app.db.models.assets import Asset
        from app.db.models.motors import MotorFamily
        from app.db.models.organization import ProductLine

        # MotorModel.family_id is required — ensure a default family stub exists
        product_line = self.session.scalars(select(ProductLine).limit(1)).first()
        if product_line is None:
            product_line = ProductLine(
                code="DEFAULT",
                name="Default Product Line",
            )
            self.session.add(product_line)
            self.session.flush()

        family = self.session.scalars(
            select(MotorFamily)
            .where(MotorFamily.product_line_id == product_line.id)
            .limit(1)
        ).first()
        if family is None:
            family = MotorFamily(
                code="DEFAULT",
                name="Default Motor Family",
                product_line_id=product_line.id,
            )
            self.session.add(family)
            self.session.flush()

        asset = Asset(
            asset_type="motor",
            name=code,
            asset_tag=f"motor:{code}",
            status="stub",
            description="Created by graph sync",
        )
        self.session.add(asset)
        self.session.flush()
        model = MotorModel(
            code=code,
            name=code,
            family_id=family.id,
            asset_id=asset.id,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def _get_document(self, document_id: str) -> Document:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.catalog_entry))
        )
        document = self.session.scalars(stmt).first()
        if document is None:
            raise NotFoundError(
                "Document not found", details={"document_id": document_id}
            )
        return document
