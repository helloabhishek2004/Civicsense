"""add dynamic priority ranking fields to issues

Revision ID: 0010_add_issue_priority_fields
Revises: 0009_add_report_issue_matches
Create Date: 2026-09-13 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_add_issue_priority_fields"
down_revision: str | None = "0009_add_report_issue_matches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("issues") as batch_op:
        batch_op.add_column(sa.Column("priority_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("priority_level", sa.String(32), nullable=True))
        batch_op.add_column(
            sa.Column("priority_computed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("priority_breakdown", sa.JSON(), nullable=True))

        # Index for ranked queries (descending priority)
        batch_op.create_index(
            "ix_issues_priority_score",
            ["priority_score"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("issues") as batch_op:
        batch_op.drop_index("ix_issues_priority_score")
        batch_op.drop_column("priority_breakdown")
        batch_op.drop_column("priority_computed_at")
        batch_op.drop_column("priority_level")
        batch_op.drop_column("priority_score")
