"""Add citizen_email and citizen_postal_code columns to reports table

Revision ID: 0005_add_citizen_email_postal_code
Revises: 0004_add_citizen_name_phone
Create Date: 2026-09-12 13:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_add_citizen_email_postal_code"
down_revision: str | None = "0004_add_citizen_name_phone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("citizen_email", sa.String(255), nullable=True))
    op.add_column("reports", sa.Column("citizen_postal_code", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "citizen_postal_code")
    op.drop_column("reports", "citizen_email")
