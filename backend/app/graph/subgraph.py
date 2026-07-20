"""React Flow-ready subgraph projection for a single motor (Phase 3).

Builds nodes/edges directly from PostgreSQL relationships (documents,
drawing numbers, related motors) rather than requiring a live Neo4j query,
so the graph view always renders even when Neo4j is unavailable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.motors.documents import (
    get_drawing_numbers_for_motor,
    get_linked_documents,
    get_related_motor_models,
    resolve_motor_model,
)


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    metadata: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str


class SubgraphOut(BaseModel):
    motor_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphSubgraphService:
    """Assemble a React Flow node/edge subgraph centered on one motor."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def build(self, motor_id: str) -> SubgraphOut:
        model = resolve_motor_model(self.session, motor_id)

        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        motor_node_id = f"motor:{model.id}"
        nodes[motor_node_id] = GraphNode(
            id=motor_node_id,
            label=model.name,
            type="motor",
            metadata={
                "code": model.code,
                "is_hero": bool((model.extra_metadata or {}).get("is_hero")),
            },
        )

        documents = get_linked_documents(self.session, model)
        for doc in documents:
            category = (
                doc.catalog_entry.doc_category if doc.catalog_entry else doc.doc_type
            )
            doc_node_id = f"doc:{doc.id}"
            nodes[doc_node_id] = GraphNode(
                id=doc_node_id,
                label=doc.title,
                type="document",
                metadata={"doc_category": category, "status": doc.status},
            )
            rel = f"HAS_{(category or 'document').upper()}"
            edges.append(
                GraphEdge(
                    id=f"{motor_node_id}->{doc_node_id}",
                    source=motor_node_id,
                    target=doc_node_id,
                    label=rel,
                )
            )

        drawings = get_drawing_numbers_for_motor(self.session, model)
        doc_by_id = {d.id: d for d in documents}
        for drawing in drawings:
            drawing_node_id = f"drawing:{drawing.id}"
            nodes[drawing_node_id] = GraphNode(
                id=drawing_node_id,
                label=drawing.drawing_number,
                type="drawing",
            )
            edges.append(
                GraphEdge(
                    id=f"{motor_node_id}->{drawing_node_id}",
                    source=motor_node_id,
                    target=drawing_node_id,
                    label="IDENTIFIED_BY",
                )
            )
            for link in drawing.document_links or []:
                if link.document_id in doc_by_id:
                    doc_node_id = f"doc:{link.document_id}"
                    edges.append(
                        GraphEdge(
                            id=f"{doc_node_id}->{drawing_node_id}",
                            source=doc_node_id,
                            target=drawing_node_id,
                            label="LINKED_VIA",
                        )
                    )

        related = get_related_motor_models(self.session, model, limit=8)
        for other in related:
            other_node_id = f"motor:{other.id}"
            nodes[other_node_id] = GraphNode(
                id=other_node_id,
                label=other.name,
                type="motor",
                metadata={"code": other.code},
            )
            relation = (
                "SAME_FAMILY"
                if other.family_id == model.family_id
                else "SHARES_DRAWING"
            )
            edges.append(
                GraphEdge(
                    id=f"{motor_node_id}->{other_node_id}:{relation}",
                    source=motor_node_id,
                    target=other_node_id,
                    label=relation,
                )
            )

        return SubgraphOut(
            motor_id=model.id,
            nodes=list(nodes.values()),
            edges=edges,
        )
