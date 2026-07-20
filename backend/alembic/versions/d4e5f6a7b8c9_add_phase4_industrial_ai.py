"""Phase 4 Alembic migration — AI, compliance tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "regulations",
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("jurisdiction", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_regulations_code", "regulations", ["code"])

    op.create_table(
        "compliance_requirements",
        sa.Column("regulation_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("evidence_doc_categories", sa.JSON(), nullable=True),
        sa.Column("evidence_keywords", sa.JSON(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["regulation_id"], ["regulations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        "ix_compliance_requirements_code", "compliance_requirements", ["code"]
    )
    op.create_index(
        "ix_compliance_requirements_asset_type",
        "compliance_requirements",
        ["asset_type"],
    )

    op.create_table(
        "certifications",
        sa.Column("motor_id", sa.String(length=36), nullable=True),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("cert_type", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["motor_id"], ["motor_models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_certifications_code", "certifications", ["code"])
    op.create_index("ix_certifications_motor_id", "certifications", ["motor_id"])

    op.create_table(
        "compliance_evidence",
        sa.Column("requirement_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("motor_id", sa.String(length=36), nullable=True),
        sa.Column("certification_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["certification_id"], ["certifications.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["motor_id"], ["motor_models.id"]),
        sa.ForeignKeyConstraint(
            ["requirement_id"], ["compliance_requirements.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requirement_id",
            "document_id",
            "motor_id",
            name="uq_compliance_evidence_req_doc_motor",
        ),
    )
    op.create_index(
        "ix_compliance_evidence_requirement_id",
        "compliance_evidence",
        ["requirement_id"],
    )
    op.create_index(
        "ix_compliance_evidence_motor_id", "compliance_evidence", ["motor_id"]
    )

    op.create_table(
        "copilot_sessions",
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("motor_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["motor_id"], ["motor_models.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_copilot_sessions_motor_id", "copilot_sessions", ["motor_id"])
    op.create_index("ix_copilot_sessions_user_id", "copilot_sessions", ["user_id"])

    op.create_table(
        "copilot_messages",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("retrieval_trace_id", sa.String(length=36), nullable=True),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["retrieval_trace_id"], ["retrieval_traces.id"]
        ),
        sa.ForeignKeyConstraint(["session_id"], ["copilot_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_copilot_messages_session_id", "copilot_messages", ["session_id"]
    )

    op.create_table(
        "feedback_ratings",
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("message_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["message_id"], ["copilot_messages.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["copilot_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("feedback_ratings")
    op.drop_table("copilot_messages")
    op.drop_table("copilot_sessions")
    op.drop_table("compliance_evidence")
    op.drop_table("certifications")
    op.drop_table("compliance_requirements")
    op.drop_table("regulations")
