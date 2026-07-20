"""Phase 2.10 validation — hero motor evidence chain on the real local corpus.

Run from backend/:
  python scripts/validate_phase2_hero.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.citations.service import CitationService  # noqa: E402
from app.core.config import Settings, clear_settings_cache, get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models.documents import (  # noqa: E402
    Document,
    DocumentCatalog,
    DocumentVersion,
)
from app.documents.classification import (  # noqa: E402
    classify_document,
    guess_mime_type,
)
from app.extraction.service import ExtractionService  # noqa: E402
from app.graph.sync import GraphSyncService  # noqa: E402
from app.indexing.chunk_service import ChunkService  # noqa: E402
from app.indexing.embedding_service import EmbeddingService  # noqa: E402
from app.indexing.embeddings import (  # noqa: E402
    HashEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from app.indexing.pipeline import priority_for_category  # noqa: E402
from app.indexing.qdrant_index import InMemoryQdrantIndex, QdrantIndex  # noqa: E402
from app.indexing.service import ParseService  # noqa: E402
from app.indexing.vector_service import VectorIndexService  # noqa: E402
from app.knowledge.retrieval import HybridRetrievalService  # noqa: E402
from app.storage.backends.local import LocalObjectStorage  # noqa: E402
from app.storage.service import StorageService  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

HERO = "Low_Voltage_Motor - 001"


def _corpus_root(settings: Settings) -> Path:
    raw = (settings.corpus_local_root or "").strip()
    if not raw:
        raise SystemExit("Set CORPUS_LOCAL_ROOT to the dataset root in .env")
    path = Path(raw)
    if not path.exists():
        raise SystemExit(f"Corpus path does not exist: {path}")
    return path


def _pick_priority_files(hero_root: Path, limit: int = 8) -> list[Path]:
    """Prefer manuals, datasheets, regulations, drawings (readable sizes)."""
    cats = [
        ("Instructions And Manuals", ("*.pdf",)),
        ("spare parts or product descriptions", ("*.pdf",)),
        ("regulations", ("*.xml", "*.csv")),
        ("incident or inspection", ("*.pdf",)),
        ("drawing/Dimension_Drawings", ("*.pdf",)),
        ("drawing", ("*.pdf",)),
    ]
    picked: list[Path] = []
    for folder, patterns in cats:
        base = hero_root / folder
        if not base.exists():
            continue
        files: list[Path] = []
        for pattern in patterns:
            files.extend(base.rglob(pattern))
        files = sorted(files, key=lambda p: p.stat().st_size)
        for f in files:
            if f.suffix.lower() == ".py":
                continue
            size = f.stat().st_size
            if size < 500 or size > 5_000_000:
                continue
            picked.append(f)
            if len(picked) >= limit:
                return picked
    return picked


def main() -> int:
    clear_settings_cache()
    # Load from repo-root / backend .env via pydantic-settings
    base = get_settings()
    corpus = _corpus_root(base)
    hero_root = corpus / "Motors" / HERO / "Low_Voltage_Motor"
    if not hero_root.exists():
        raise SystemExit(f"Hero motor folder missing: {hero_root}")

    files = _pick_priority_files(hero_root)
    if not files:
        raise SystemExit("No priority files found under hero motor")

    print(f"Corpus: {corpus}")
    print(f"Hero: {hero_root}")
    print(f"Selected {len(files)} files:")
    for f in files:
        rel = f.relative_to(corpus)
        classification = classify_document(
            name=f.name, folder_path=str(rel.parent).replace("\\", "/")
        )
        pri = priority_for_category(classification.doc_category)
        print(f"  [{pri}] {classification.doc_category}: {rel}")

    data_dir = ROOT / ".data" / "phase2_validation"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "validate.db"
    if db_path.exists():
        db_path.unlink()
    storage_root = data_dir / "storage"
    storage_root.mkdir(exist_ok=True)

    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()

    settings = Settings(
        app_env="development",
        database_url=f"sqlite:///{db_path.as_posix()}",
        storage_backend="local",
        storage_local_root=str(storage_root),
        openai_api_key=base.openai_api_key,
        embedding_model=base.embedding_model,
        embedding_dimensions=base.embedding_dimensions,
        qdrant_url=base.qdrant_url,
        qdrant_api_key=base.qdrant_api_key,
        qdrant_collection="industrial_brain_chunks_validation",
        neo4j_uri=base.neo4j_uri,
        neo4j_user=base.neo4j_user,
        neo4j_password=base.neo4j_password,
        corpus_local_root=str(corpus),
        parse_fallback_without_azure=True,
    )
    storage = StorageService(
        LocalObjectStorage(root=str(storage_root), bucket="validation")
    )

    use_openai = bool((settings.openai_api_key or "").strip())
    provider = (
        OpenAIEmbeddingProvider(settings) if use_openai else HashEmbeddingProvider()
    )
    print(f"Embeddings: {provider.model_version} (openai={use_openai})")

    try:
        index: QdrantIndex | InMemoryQdrantIndex
        if use_openai:
            try:
                # Avoid hard-failing on client/server minor mismatch
                from qdrant_client import QdrantClient

                client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=(settings.qdrant_api_key or "").strip() or None,
                    prefer_grpc=False,
                    check_compatibility=False,
                )
                index = QdrantIndex(settings, client=client)
                index.dimensions = provider.dimensions
                index.ensure_collection()
                print(
                    f"Qdrant: {settings.qdrant_url} / {settings.qdrant_collection}"
                )
            except Exception as exc:  # noqa: BLE001
                print(f"Qdrant unavailable ({exc}); using in-memory index")
                index = InMemoryQdrantIndex(dimensions=provider.dimensions)
        else:
            print("Using in-memory vector index (no OPENAI_API_KEY)")
            index = InMemoryQdrantIndex(dimensions=provider.dimensions)

        parse = ParseService(session, storage, settings)
        extract = ExtractionService(session)
        chunks = ChunkService(session)
        embed = EmbeddingService(session, settings, provider=provider)
        vectors = VectorIndexService(
            session, settings, index=index, embedding_service=embed
        )
        graph = GraphSyncService(session, settings)
        retrieval = HybridRetrievalService(
            session, settings, vector_service=vectors, graph_service=graph
        )
        citations = CitationService(session)

        processed: list[str] = []
        for path in files:
            rel = path.relative_to(corpus)
            rel_folder = str(rel.parent).replace("\\", "/")
            classification = classify_document(name=path.name, folder_path=rel_folder)
            raw = path.read_bytes()
            key = f"hero/{path.name}"
            stored = storage.upload(
                key,
                raw,
                content_type=guess_mime_type(path.name) or "application/octet-stream",
            )
            catalog = DocumentCatalog(
                drive_file_id=f"validate:{path.as_posix()}",
                name=path.name,
                folder_path=rel_folder,
                mime_type=guess_mime_type(path.name),
                size_bytes=len(raw),
                doc_category=classification.doc_category,
                doc_subtype=classification.doc_subtype,
                drawing_number=classification.drawing_number,
                motor_type_code=classification.motor_type_code or HERO,
                extra_metadata={
                    "storage_key": stored.key,
                    "storage_bucket": stored.bucket,
                },
            )
            session.add(catalog)
            session.flush()
            document = Document(
                title=path.name,
                doc_type=classification.doc_category,
                status="uploaded",
                storage_uri=f"{stored.bucket}/{stored.key}",
                catalog_id=catalog.id,
            )
            session.add(document)
            session.flush()
            session.add(
                DocumentVersion(
                    version=1,
                    storage_uri=document.storage_uri or "",
                    document_id=document.id,
                )
            )
            session.flush()

            print(
                f"\n--- Pipeline: {path.name} "
                f"({classification.doc_category}) ---"
            )
            try:
                parse.parse_document(document.id)
                extract.extract_document(document.id)
                chunks.chunk_document(document.id)
                vectors.index_document(document.id)
                graph.sync_document(document.id)
                document.status = "ready"
                session.commit()
                processed.append(document.id)
                print(f"  OK document_id={document.id}")
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                print(f"  FAIL: {exc}")

        if not processed:
            print("\nVALIDATION FAILED: no documents completed the pipeline")
            return 1

        neighborhood = graph.neighborhood(HERO)
        result = retrieval.retrieve(
            "installation commissioning lockout energy efficiency",
            motor_type_code=HERO,
            limit=5,
        )
        refs = citations.format_from_results(result["results"])
        verification = (
            citations.verify(" ".join(refs)) if refs else {"valid": False}
        )
        trace = citations.persist_trace(
            query_text="installation commissioning lockout energy efficiency",
            results=result["results"],
            motor_type_code=HERO,
            graph_path_strength=1.0 if neighborhood.get("documents") else 0.0,
        )
        session.commit()

        print("\n=== Phase 2.10 Validation Summary ===")
        print(f"Documents ready: {len(processed)}")
        print(
            f"Graph docs linked to {HERO}: "
            f"{len(neighborhood.get('documents') or [])}"
        )
        print(f"Retrieval hits: {len(result['results'])}")
        print(f"Citations valid: {verification.get('valid')}")
        print(f"Trace confidence: {trace.confidence}")
        print(f"Channels: {result.get('channels')}")

        ok = (
            len(processed) >= 1
            and len(result["results"]) >= 1
            and bool(verification.get("valid"))
        )
        if ok:
            print("\nPHASE 2 VALIDATION GATE: PASS")
            return 0
        print("\nPHASE 2 VALIDATION GATE: FAIL")
        return 1
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
