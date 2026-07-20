"""Checklist-based compliance gap detection — Python-owned (Milestone 4.5)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.compliance import (
    Certification,
    ComplianceEvidence,
    ComplianceRequirement,
    Regulation,
)
from app.motors.documents import get_linked_documents, resolve_motor_model
from app.observability import get_logger

_logger = get_logger(__name__)

# Seed checklist aligned to Architecture demo (IEC / ATEX / LOTO evidence)
_SEED_REGULATIONS: list[dict[str, Any]] = [
    {
        "code": "IEC-60034",
        "name": "IEC 60034 Rotating Electrical Machines",
        "description": "Performance testing and rating requirements for LV motors.",
        "jurisdiction": "IEC",
    },
    {
        "code": "ATEX-2014-34-EU",
        "name": "ATEX Directive 2014/34/EU",
        "description": "Equipment for explosive atmospheres.",
        "jurisdiction": "EU",
    },
    {
        "code": "LOTO-OSHA-1910.147",
        "name": "Lockout/Tagout Control of Hazardous Energy",
        "description": "Energy isolation before maintenance.",
        "jurisdiction": "OSHA",
    },
]

_SEED_REQUIREMENTS: list[dict[str, Any]] = [
    {
        "code": "REQ-IEC-TEST-REPORT",
        "regulation_code": "IEC-60034",
        "title": "Performance test report on file",
        "description": "IEC 60034 performance / type test evidence for the motor.",
        "evidence_doc_categories": ["test_report", "performance_test"],
        "evidence_keywords": ["iec 60034", "efficiency", "temperature rise"],
        "severity": "high",
    },
    {
        "code": "REQ-IEC-DATASHEET",
        "regulation_code": "IEC-60034",
        "title": "Product datasheet / nameplate specs",
        "description": "Rated specs must be documented in a datasheet.",
        "evidence_doc_categories": ["datasheet", "specification"],
        "evidence_keywords": ["rated power", "frame", "ie class"],
        "severity": "medium",
    },
    {
        "code": "REQ-ATEX-CERT",
        "regulation_code": "ATEX-2014-34-EU",
        "title": "ATEX / Ex certification",
        "description": "ATEX certificate evidencing explosive atmosphere suitability.",
        "evidence_doc_categories": ["certificate", "certification", "atex"],
        "evidence_keywords": ["atex", "ex d", "ex e", "zone"],
        "severity": "high",
    },
    {
        "code": "REQ-LOTO-SOP",
        "regulation_code": "LOTO-OSHA-1910.147",
        "title": "LOTO procedure before maintenance",
        "description": "Lockout/Tagout SOP applicable before motor maintenance.",
        "evidence_doc_categories": ["safety", "procedure", "manual", "maintenance"],
        "evidence_keywords": ["loto", "lockout", "tagout", "isolation"],
        "severity": "critical",
    },
    {
        "code": "REQ-DRAWING-OUTLINE",
        "regulation_code": "IEC-60034",
        "title": "Outline / dimension drawing",
        "description": "Engineering drawing cross-reference for installation.",
        "evidence_doc_categories": ["drawing", "outline_drawing", "dimension_drawing"],
        "evidence_keywords": ["3gzf", "outline", "dimension"],
        "severity": "medium",
    },
]


class ComplianceEngine:
    """Deterministic requirements ↔ evidence matching (no LLM scoring)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_seed(self) -> None:
        """Idempotently seed regulations + checklist requirements."""
        for reg in _SEED_REGULATIONS:
            existing = self.session.scalars(
                select(Regulation).where(Regulation.code == reg["code"])
            ).first()
            if existing is None:
                self.session.add(
                    Regulation(
                        code=reg["code"],
                        name=reg["name"],
                        description=reg.get("description"),
                        jurisdiction=reg.get("jurisdiction"),
                    )
                )
        self.session.flush()

        reg_by_code = {
            r.code: r for r in self.session.scalars(select(Regulation)).all()
        }
        for req in _SEED_REQUIREMENTS:
            existing = self.session.scalars(
                select(ComplianceRequirement).where(
                    ComplianceRequirement.code == req["code"]
                )
            ).first()
            if existing is not None:
                continue
            regulation = reg_by_code.get(req["regulation_code"])
            self.session.add(
                ComplianceRequirement(
                    regulation_id=regulation.id if regulation else None,
                    code=req["code"],
                    title=req["title"],
                    description=req.get("description"),
                    asset_type="motor",
                    evidence_doc_categories=req.get("evidence_doc_categories"),
                    evidence_keywords=req.get("evidence_keywords"),
                    severity=req.get("severity", "medium"),
                )
            )
        self.session.flush()

    def assess_motor(self, motor_id: str) -> dict[str, Any]:
        self.ensure_seed()
        model = resolve_motor_model(self.session, motor_id)
        documents = get_linked_documents(self.session, model)
        requirements = list(
            self.session.scalars(
                select(ComplianceRequirement).where(
                    ComplianceRequirement.asset_type == "motor"
                )
            ).all()
        )

        items: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []
        met = 0

        for req in requirements:
            match = self._match_requirement(req, documents)
            status = "met" if match else "gap"
            if match:
                met += 1
                self._upsert_evidence(req.id, model.id, match["document_id"])
                if match.get("is_cert"):
                    self._upsert_certification(
                        model.id,
                        match["document_id"],
                        code=req.code,
                        name=req.title,
                    )
            else:
                gaps.append(
                    {
                        "requirement_code": req.code,
                        "title": req.title,
                        "severity": req.severity,
                        "regulation_id": req.regulation_id,
                    }
                )
            items.append(
                {
                    "requirement_code": req.code,
                    "title": req.title,
                    "severity": req.severity,
                    "status": status,
                    "evidence": match,
                    "description": req.description,
                }
            )

        total = len(requirements) or 1
        return {
            "motor_id": model.id,
            "motor_code": model.code,
            "coverage": round(met / total, 3),
            "met": met,
            "total": len(requirements),
            "gaps": gaps,
            "items": items,
        }

    def list_requirements(self) -> list[dict[str, Any]]:
        self.ensure_seed()
        rows = self.session.scalars(select(ComplianceRequirement)).all()
        return [
            {
                "id": r.id,
                "code": r.code,
                "title": r.title,
                "description": r.description,
                "severity": r.severity,
                "evidence_doc_categories": r.evidence_doc_categories,
            }
            for r in rows
        ]

    def _match_requirement(
        self,
        req: ComplianceRequirement,
        documents: list[Any],
    ) -> dict[str, Any] | None:
        categories = {str(c).lower() for c in (req.evidence_doc_categories or [])}
        keywords = [str(k).lower() for k in (req.evidence_keywords or [])]

        for doc in documents:
            cat = (
                (doc.catalog_entry.doc_category if doc.catalog_entry else None)
                or doc.doc_type
                or ""
            ).lower()
            title = (doc.title or "").lower()
            cat_hit = (
                any(c in cat or cat.startswith(c.rstrip("s")) for c in categories)
                if categories
                else False
            )
            kw_hit = (
                any(k in title or k in cat for k in keywords) if keywords else False
            )
            if cat_hit or kw_hit:
                return {
                    "document_id": doc.id,
                    "title": doc.title,
                    "doc_category": cat,
                    "confidence": 0.85 if cat_hit else 0.65,
                    "is_cert": "cert" in cat or "atex" in cat or "atex" in title,
                }
        return None

    def _upsert_evidence(
        self,
        requirement_id: str,
        motor_id: str,
        document_id: str,
    ) -> None:
        existing = self.session.scalars(
            select(ComplianceEvidence).where(
                ComplianceEvidence.requirement_id == requirement_id,
                ComplianceEvidence.motor_id == motor_id,
                ComplianceEvidence.document_id == document_id,
            )
        ).first()
        if existing:
            return
        self.session.add(
            ComplianceEvidence(
                requirement_id=requirement_id,
                motor_id=motor_id,
                document_id=document_id,
                status="matched",
                confidence=0.8,
            )
        )
        self.session.flush()

    def _upsert_certification(
        self,
        motor_id: str,
        document_id: str,
        *,
        code: str,
        name: str,
    ) -> None:
        existing = self.session.scalars(
            select(Certification).where(
                Certification.motor_id == motor_id,
                Certification.document_id == document_id,
            )
        ).first()
        if existing:
            return
        self.session.add(
            Certification(
                motor_id=motor_id,
                document_id=document_id,
                code=code,
                name=name,
                cert_type="compliance",
                status="active",
            )
        )
        self.session.flush()
