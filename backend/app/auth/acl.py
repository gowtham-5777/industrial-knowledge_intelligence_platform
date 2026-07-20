"""Document ACL filtering before retrieval / LLM (Milestone 5.1.2)."""

from __future__ import annotations

from typing import Any, Collection

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.documents import DocumentAcl
from app.db.models.system import User, UserRole
from app.observability import get_logger

_logger = get_logger(__name__)

# Roles that bypass ACL filtering (Architecture SystemAdmin / Auditor read).
ACL_BYPASS_ROLES: frozenset[str] = frozenset({"SystemAdmin", "Auditor"})

# Classification → minimum role set when ACL.allowed_roles is empty.
CLASSIFICATION_DEFAULT_ROLES: dict[str, frozenset[str]] = {
    "public": frozenset(
        {
            "PlantOperator",
            "MaintenanceEngineer",
            "ReliabilityEngineer",
            "QualityEngineer",
            "ComplianceOfficer",
            "PlantManager",
            "SystemAdmin",
            "Auditor",
        }
    ),
    "internal": frozenset(
        {
            "PlantOperator",
            "MaintenanceEngineer",
            "ReliabilityEngineer",
            "QualityEngineer",
            "ComplianceOfficer",
            "PlantManager",
            "SystemAdmin",
            "Auditor",
        }
    ),
    "restricted": frozenset(
        {
            "ReliabilityEngineer",
            "ComplianceOfficer",
            "PlantManager",
            "SystemAdmin",
            "Auditor",
        }
    ),
}


def user_role_codes(user: User | None) -> set[str]:
    if user is None:
        return set()
    return {link.role.code for link in user.roles if link.role is not None}


def user_bypasses_acl(user: User | None) -> bool:
    return bool(user_role_codes(user) & ACL_BYPASS_ROLES)


class DocumentAclFilter:
    """Filter document/chunk hits so LLM never sees unauthorized content."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_default_acl(
        self,
        document_id: str,
        *,
        classification: str = "internal",
        allowed_roles: list[str] | None = None,
        plant_id: str | None = None,
    ) -> DocumentAcl:
        existing = self.session.scalars(
            select(DocumentAcl).where(DocumentAcl.document_id == document_id)
        ).first()
        if existing is not None:
            return existing
        row = DocumentAcl(
            document_id=document_id,
            classification=classification,
            allowed_roles=allowed_roles,
            plant_id=plant_id,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def allowed_document_ids(
        self,
        document_ids: Collection[str],
        *,
        user: User | None,
    ) -> set[str]:
        ids = {d for d in document_ids if d}
        if not ids:
            return set()
        if user_bypasses_acl(user):
            return ids

        roles = user_role_codes(user)
        acls = list(
            self.session.scalars(
                select(DocumentAcl).where(DocumentAcl.document_id.in_(ids))
            ).all()
        )
        acl_by_doc = {a.document_id: a for a in acls}
        allowed: set[str] = set()
        for doc_id in ids:
            acl = acl_by_doc.get(doc_id)
            if acl is None:
                # No ACL row → treat as internal (all authenticated roles).
                if roles & CLASSIFICATION_DEFAULT_ROLES["internal"]:
                    allowed.add(doc_id)
                continue
            if self._acl_permits(acl, roles):
                allowed.add(doc_id)
        return allowed

    def filter_retrieval_results(
        self,
        results: list[dict[str, Any]],
        *,
        user: User | None,
    ) -> list[dict[str, Any]]:
        if not results:
            return results
        if user_bypasses_acl(user):
            return results
        doc_ids = {r.get("document_id") for r in results if r.get("document_id")}
        allowed = self.allowed_document_ids(doc_ids, user=user)
        filtered = [r for r in results if r.get("document_id") in allowed]
        dropped = len(results) - len(filtered)
        if dropped:
            _logger.info(
                "acl_filtered_retrieval",
                extra={"dropped": dropped, "kept": len(filtered)},
            )
        return filtered

    @staticmethod
    def _acl_permits(acl: DocumentAcl, roles: set[str]) -> bool:
        if acl.allowed_roles:
            return bool(roles & set(acl.allowed_roles))
        defaults = CLASSIFICATION_DEFAULT_ROLES.get(
            (acl.classification or "internal").lower(),
            CLASSIFICATION_DEFAULT_ROLES["internal"],
        )
        return bool(roles & defaults)


def load_user_with_roles(session: Session, user_id: str | None) -> User | None:
    if not user_id:
        return None
    from sqlalchemy.orm import selectinload

    return session.scalars(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(UserRole.role))
    ).first()
