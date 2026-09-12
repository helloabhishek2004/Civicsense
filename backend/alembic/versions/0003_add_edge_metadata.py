"""Add edge_metadata column to reports table

Revision ID: 0003_add_edge_metadata
Revises: 0002_ai_jobs_and_events
Create Date: 2026-09-12 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_edge_metadata"
down_revision: str | None = "0002_ai_jobs_and_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("edge_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "edge_metadata")
