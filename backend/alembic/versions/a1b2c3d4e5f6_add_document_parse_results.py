"""add_document_parse_results

Revision ID: a1b2c3d4e5f6
Revises: bda52b107059
Create Date: 2026-07-20 23:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "bda52b107059"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_parse_results",
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=True),
        sa.Column("indexing_job_id", sa.String(length=36), nullable=True),
        sa.Column("tier", sa.String(length=8), nullable=False),
        sa.Column("parser_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("pages", sa.JSON(), nullable=True),
        sa.Column("tables", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["indexing_job_id"], ["indexing_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_parse_results_document_id"),
        "document_parse_results",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_parse_results_document_version_id"),
        "document_parse_results",
        ["document_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_parse_results_indexing_job_id"),
        "document_parse_results",
        ["indexing_job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_parse_results_status"),
        "document_parse_results",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_parse_results_tier"),
        "document_parse_results",
        ["tier"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_document_parse_results_tier"), table_name="document_parse_results"
    )
    op.drop_index(
        op.f("ix_document_parse_results_status"), table_name="document_parse_results"
    )
    op.drop_index(
        op.f("ix_document_parse_results_indexing_job_id"),
        table_name="document_parse_results",
    )
    op.drop_index(
        op.f("ix_document_parse_results_document_version_id"),
        table_name="document_parse_results",
    )
    op.drop_index(
        op.f("ix_document_parse_results_document_id"),
        table_name="document_parse_results",
    )
    op.drop_table("document_parse_results")
