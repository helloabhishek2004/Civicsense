"""add text embedding columns for similarity matching

Revision ID: 0008_add_similarity_embeddings
Revises: 0007_add_departments_and_assignments
Create Date: 2026-09-13 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_add_similarity_embeddings"
down_revision: str | None = "0007_add_departments_and_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add text_embedding and embedding_model_version to reports
    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("text_embedding", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("embedding_model_version", sa.String(64), nullable=True))

    # Add text_embedding and embedding_model_version to issues
    with op.batch_alter_table("issues") as batch_op:
        batch_op.add_column(sa.Column("text_embedding", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("embedding_model_version", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("issues") as batch_op:
        batch_op.drop_column("embedding_model_version")
        batch_op.drop_column("text_embedding")

    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_column("embedding_model_version")
        batch_op.drop_column("text_embedding")
