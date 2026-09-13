"""add report_issue_matches table for dedup review workflow

Revision ID: 0009_add_report_issue_matches
Revises: 0008_add_similarity_embeddings
Create Date: 2026-09-13 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_add_report_issue_matches"
down_revision: str | None = "0008_add_similarity_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_issue_matches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "report_id",
            sa.Uuid(),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "issue_id",
            sa.Uuid(),
            sa.ForeignKey("issues.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("action", sa.String(32), nullable=False, index=True),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="PENDING", index=True
        ),
        sa.Column("combined_score", sa.Float(), nullable=False),
        sa.Column("text_similarity", sa.Float(), nullable=False),
        sa.Column("distance_meters", sa.Float(), nullable=False),
        sa.Column("category_match", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.JSON(), nullable=True),
        sa.Column("embedding_model_version", sa.String(64), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_id", sa.String(128), nullable=True),
        sa.Column("review_notes", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("report_issue_matches")
