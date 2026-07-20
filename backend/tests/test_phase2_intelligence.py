"""Tests for Phase 2 Document Intelligence (Milestones 2.2–2.9)."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import app.db.models  # noqa: F401
import pytest
from app.citations.service import CitationService, format_citation
from app.core.config import Settings
from app.db.base import Base
from app.db.models.documents import Document, DocumentCatalog, DocumentVersion
from app.db.models.parsing import DocumentParseResult
from app.extraction.extractors import run_extractors
from app.extraction.service import ExtractionService
from app.graph.sync import GraphSyncService, InMemoryGraphStore
from app.indexing.chunk_service import ChunkService
from app.indexing.chunkers import chunk_document
from app.indexing.embedding_service import EmbeddingService
from app.indexing.embeddings import HashEmbeddingProvider
from app.indexing.pipeline import priority_for_category
from app.indexing.qdrant_index import InMemoryQdrantIndex
from app.indexing.vector_service import VectorIndexService
from app.knowledge.retrieval import HybridRetrievalService, reciprocal_rank_fusion
from app.storage.backends.local import LocalObjectStorage
from app.storage.service import StorageService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'phase2.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def storage(tmp_path: Path) -> StorageService:
    root = tmp_path / "storage"
    root.mkdir()
    return StorageService(LocalObjectStorage(root=str(root), bucket="test-bucket"))


def _seed_parsed_document(
    session: Session,
    *,
    category: str = "test_report",
    filename: str = "9AKK10103A0473_report.pdf",
    text: str = "IEC 60034 Efficiency 95.2% Power factor 0.88",
    tables: list | None = None,
) -> Document:
    catalog = DocumentCatalog(
        drive_file_id=f"local:{filename}",
        name=filename,
        folder_path=(
            "Motors/Low_Voltage_Motor - 001/Low_Voltage_Motor/incident or inspection"
        ),
        mime_type="application/pdf",
        doc_category=category,
        drawing_number=None,
        motor_type_code="Low_Voltage_Motor - 001",
        extra_metadata={},
    )
    session.add(catalog)
    session.flush()
    document = Document(
        title=filename,
        doc_type=category,
        status="parsed",
        catalog_id=catalog.id,
    )
    session.add(document)
    session.flush()
    session.add(
        DocumentVersion(
            version=1, storage_uri="test-bucket/x.pdf", document_id=document.id
        )
    )
    if tables is None:
        tables = [
            {
                "page": 1,
                "rows": [
                    ["Parameter", "Unit", "Rated", "Measured"],
                    ["Efficiency", "%", "95.5", "95.2"],
                    ["Power factor", "-", "0.88", "0.87"],
                ],
                "markdown": "| Parameter | Unit | Rated | Measured |",
                "source": "test",
            }
        ]
    session.add(
        DocumentParseResult(
            document_id=document.id,
            tier="T1",
            parser_name="test",
            status="succeeded",
            page_count=1,
            full_text=text,
            pages=[{"page": 1, "text": text}],
            tables=tables,
            warnings=[],
            extra_metadata={},
        )
    )
    session.flush()
    return document


def test_drawing_and_9akk_extractors() -> None:
    bundle = run_extractors(
        filename="9AKK10103A0473_en__Rev-A.pdf",
        folder_path="Motors/Low_Voltage_Motor - 001/drawing",
        full_text="See also 3GZF500725-144 sheet A1",
        tables=[],
        doc_category="drawing",
    )
    types = {e.entity_type: e.value for e in bundle.entities}
    assert "drawing_number" in types
    assert types["drawing_number"].startswith("9AKK") or any(
        e.value.startswith("9AKK")
        for e in bundle.entities
        if e.entity_type == "drawing_number"
    )
    assert any(
        e.entity_type == "sheet_id" and e.value == "A1" for e in bundle.entities
    ) or any("3GZF" in e.value for e in bundle.entities)


def test_iec_table_measurements() -> None:
    bundle = run_extractors(
        filename="report.pdf",
        full_text="IEC 60034 Performance Test",
        tables=[
            {
                "page": 1,
                "rows": [
                    ["Parameter", "Unit", "Rated", "Measured"],
                    ["Efficiency", "%", "95.5", "95.2"],
                    ["Power factor", "-", "0.88", "0.87"],
                ],
            }
        ],
        doc_category="test_report",
    )
    params = {m.parameter: m.measured_value for m in bundle.measurements}
    assert params.get("efficiency") == "95.2"
    assert params.get("power_factor") == "0.87"
    assert bundle.standard and "60034" in bundle.standard


def test_extraction_service_persists(db_session: Session) -> None:
    document = _seed_parsed_document(db_session)
    result = ExtractionService(db_session).extract_document(document.id)
    assert result["candidate_count"] >= 1
    assert result["measurement_count"] >= 2
    assert document.status == "extracted"


def test_chunk_metadata_payload() -> None:
    drafts = chunk_document(
        doc_category="test_report",
        full_text="body",
        tables=[
            {
                "page": 1,
                "rows": [["Parameter", "Measured"], ["Efficiency", "95.2"]],
                "markdown": (
                    "| Parameter | Measured |\n| --- | --- |\n| Efficiency | 95.2 |"
                ),
            }
        ],
    )
    assert drafts
    assert drafts[0].parent_section
    assert "Efficiency" in drafts[0].text or "95.2" in drafts[0].text


def test_chunk_service_persists(db_session: Session) -> None:
    document = _seed_parsed_document(db_session)
    out = ChunkService(db_session).chunk_document(document.id)
    assert out["chunk_count"] >= 1
    chunk = out["chunks"][0]
    assert chunk["document_id"] == document.id
    assert "drawing_numbers" in chunk or chunk.get("motor_models") is not None


def test_embedding_version_stored(db_session: Session) -> None:
    document = _seed_parsed_document(db_session)
    ChunkService(db_session).chunk_document(document.id)
    settings = Settings(app_env="test", database_url="sqlite:///:memory:")
    service = EmbeddingService(db_session, settings, provider=HashEmbeddingProvider())
    result = service.embed_document(document.id)
    assert result["embedded_count"] >= 1
    assert result["model_version"] == "hash:hash-embed-v1"
    chunks = ChunkService(db_session).get_chunks(document.id)
    assert chunks[0]["embedding_model_version"] == "hash:hash-embed-v1"


def test_qdrant_filter_search(db_session: Session) -> None:
    document = _seed_parsed_document(db_session)
    ChunkService(db_session).chunk_document(document.id)
    settings = Settings(app_env="test", database_url="sqlite:///:memory:")
    provider = HashEmbeddingProvider()
    index = InMemoryQdrantIndex(dimensions=provider.dimensions)
    vectors = VectorIndexService(
        db_session,
        settings,
        index=index,
        embedding_service=EmbeddingService(db_session, settings, provider=provider),
    )
    indexed = vectors.index_document(document.id)
    assert indexed["upserted"] >= 1
    hits = vectors.search("efficiency", motor_model="Low_Voltage_Motor - 001", limit=5)
    assert hits
    assert hits[0]["payload"]["document_id"] == document.id


def test_graph_sync_motor_neighborhood(db_session: Session) -> None:
    document = _seed_parsed_document(db_session)
    ExtractionService(db_session).extract_document(document.id)
    store = InMemoryGraphStore()
    service = GraphSyncService(db_session, Settings(app_env="test"), client=store)
    out = service.sync_document(document.id)
    assert out["motor_type_code"]
    neighborhood = service.neighborhood(out["motor_type_code"])
    assert neighborhood["motor"]
    assert any(d.get("id") == document.id for d in neighborhood["documents"])


def test_hybrid_retrieval_and_citations(db_session: Session) -> None:
    document = _seed_parsed_document(db_session)
    ExtractionService(db_session).extract_document(document.id)
    ChunkService(db_session).chunk_document(document.id)
    settings = Settings(app_env="test", database_url="sqlite:///:memory:")
    provider = HashEmbeddingProvider()
    index = InMemoryQdrantIndex(dimensions=provider.dimensions)
    graph = GraphSyncService(db_session, settings, client=InMemoryGraphStore())
    graph.sync_document(document.id)
    vectors = VectorIndexService(
        db_session,
        settings,
        index=index,
        embedding_service=EmbeddingService(db_session, settings, provider=provider),
    )
    vectors.index_document(document.id)
    retrieval = HybridRetrievalService(
        db_session, settings, vector_service=vectors, graph_service=graph
    )
    result = retrieval.retrieve(
        "efficiency measured",
        motor_type_code="Low_Voltage_Motor - 001",
        limit=5,
    )
    assert result["results"]
    citations = CitationService(db_session)
    refs = citations.format_from_results(result["results"])
    assert refs
    assert refs[0].startswith("[")
    verification = citations.verify(" ".join(refs))
    assert verification["valid"] is True
    trace = citations.persist_trace(
        query_text="efficiency measured",
        results=result["results"],
        motor_type_code="Low_Voltage_Motor - 001",
    )
    assert trace.confidence is not None


def test_rrf_and_priority_order() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]])
    assert fused[0][0] in {"a", "b"}
    assert priority_for_category("test_report") < priority_for_category("drawing")
    assert priority_for_category("datasheet") < priority_for_category("drawing_cad")


def test_citation_format() -> None:
    ref = format_citation(
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    )
    assert ref == (
        "[11111111-1111-1111-1111-111111111111:" "22222222-2222-2222-2222-222222222222]"
    )
