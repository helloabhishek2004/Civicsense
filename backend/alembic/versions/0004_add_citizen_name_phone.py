"""Add citizen_name and citizen_phone columns to reports table

Revision ID: 0004_add_citizen_name_phone
Revises: 0003_add_edge_metadata
Create Date: 2026-09-12 13:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_add_citizen_name_phone"
down_revision: str | None = "0003_add_edge_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("citizen_name", sa.String(128), nullable=True))
    op.add_column("reports", sa.Column("citizen_phone", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "citizen_phone")
    op.drop_column("reports", "citizen_name")
