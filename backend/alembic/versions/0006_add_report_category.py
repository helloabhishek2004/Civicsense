"""add category to report

Revision ID: 0006_add_report_category
Revises: 0005_add_citizen_email_postal_code
Create Date: 2026-09-12 14:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_add_report_category"
down_revision: str | None = "0005_add_citizen_email_postal_code"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("category", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_reports_category"), "reports", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_category"), table_name="reports")
    op.drop_column("reports", "category")
