"""add image embedding columns for visual similarity

Revision ID: 0011_add_image_embeddings
Revises: 0010_add_issue_priority_fields
Create Date: 2026-09-13 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011_add_image_embeddings"
down_revision: str | None = "0010_add_issue_priority_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add image_embedding and vision_model_version to reports
    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("image_embedding", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("vision_model_version", sa.String(64), nullable=True))

    # Add image_embedding and vision_model_version to issues
    with op.batch_alter_table("issues") as batch_op:
        batch_op.add_column(sa.Column("image_embedding", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("vision_model_version", sa.String(64), nullable=True))

    # Add visual_similarity to report_issue_matches
    with op.batch_alter_table("report_issue_matches") as batch_op:
        batch_op.add_column(
            sa.Column("visual_similarity", sa.Float(), nullable=False, server_default="0.0")
        )


def downgrade() -> None:
    with op.batch_alter_table("report_issue_matches") as batch_op:
        batch_op.drop_column("visual_similarity")

    with op.batch_alter_table("issues") as batch_op:
        batch_op.drop_column("vision_model_version")
        batch_op.drop_column("image_embedding")

    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_column("vision_model_version")
        batch_op.drop_column("image_embedding")
