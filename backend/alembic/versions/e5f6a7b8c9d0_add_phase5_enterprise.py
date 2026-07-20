"""Phase 5 Alembic migration — document ACL + dead-letter jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_acl",
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=True),
        sa.Column(
            "classification",
            sa.String(length=32),
            nullable=False,
            server_default="internal",
        ),
        sa.Column("allowed_roles", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index("ix_document_acl_document_id", "document_acl", ["document_id"])
    op.create_index("ix_document_acl_plant_id", "document_acl", ["plant_id"])
    op.create_index(
        "ix_document_acl_classification", "document_acl", ["classification"]
    )

    op.create_table(
        "dead_letter_jobs",
        sa.Column("task_name", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="open"
        ),
        sa.Column("document_id", sa.String(length=36), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dead_letter_jobs_task_name", "dead_letter_jobs", ["task_name"]
    )
    op.create_index(
        "ix_dead_letter_jobs_idempotency_key",
        "dead_letter_jobs",
        ["idempotency_key"],
    )
    op.create_index("ix_dead_letter_jobs_status", "dead_letter_jobs", ["status"])
    op.create_index(
        "ix_dead_letter_jobs_document_id", "dead_letter_jobs", ["document_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_dead_letter_jobs_document_id", table_name="dead_letter_jobs")
    op.drop_index("ix_dead_letter_jobs_status", table_name="dead_letter_jobs")
    op.drop_index(
        "ix_dead_letter_jobs_idempotency_key", table_name="dead_letter_jobs"
    )
    op.drop_index("ix_dead_letter_jobs_task_name", table_name="dead_letter_jobs")
    op.drop_table("dead_letter_jobs")
    op.drop_index("ix_document_acl_classification", table_name="document_acl")
    op.drop_index("ix_document_acl_plant_id", table_name="document_acl")
    op.drop_index("ix_document_acl_document_id", table_name="document_acl")
    op.drop_table("document_acl")
