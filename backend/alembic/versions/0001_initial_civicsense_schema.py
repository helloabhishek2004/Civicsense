"""Initial CivicSense schema: issues, reports, evidences,
model_versions, ai_analyses, verifications, resolutions

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Issues table
    op.create_table(
        "issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("primary_latitude", sa.Float(), nullable=False),
        sa.Column("primary_longitude", sa.Float(), nullable=False),
        sa.Column("report_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_issues_category", "issues", ["category"])
    op.create_index("ix_issues_status", "issues", ["status"])

    # 2. Reports table
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tracking_id", sa.String(length=32), nullable=False),
        sa.Column("citizen_id", sa.String(length=128), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "SUBMITTED",
                "AI_PROCESSING",
                "AI_PROCESSED",
                "VERIFICATION_REQUIRED",
                "VERIFIED",
                "PRIORITIZED",
                "ASSIGNED",
                "IN_PROGRESS",
                "RESOLVED",
                "RESOLUTION_VERIFIED",
                "CLOSED",
                name="reportstatus",
            ),
            nullable=False,
            server_default="SUBMITTED",
        ),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("address_hint", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_tracking_id", "reports", ["tracking_id"], unique=True)
    op.create_index("ix_reports_citizen_id", "reports", ["citizen_id"])
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_issue_id", "reports", ["issue_id"])

    # 3. Evidences table
    op.create_table(
        "evidences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column(
            "evidence_type",
            sa.Enum("IMAGE", "TEXT", "METADATA", name="evidencetype"),
            nullable=False,
        ),
        sa.Column("storage_uri", sa.String(length=512), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=True),
        sa.Column("mime_type", sa.String(length=64), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidences_report_id", "evidences", ["report_id"])

    # 4. Model Versions table
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("preprocessing_version", sa.String(length=64), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("embedding_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. AI Analyses table
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=True),
        sa.Column("predicted_category", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "severity",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="severitylevel"),
            nullable=True,
        ),
        sa.Column(
            "priority",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="prioritylevel"),
            nullable=True,
        ),
        sa.Column("evidence_agreement", sa.Float(), nullable=True),
        sa.Column("review_required", sa.Boolean(), nullable=True),
        sa.Column("analysis_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_analyses_report_id", "ai_analyses", ["report_id"])
    op.create_index("ix_ai_analyses_model_version_id", "ai_analyses", ["model_version_id"])

    # 6. Verifications table
    op.create_table(
        "verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=True),
        sa.Column(
            "decision",
            sa.Enum("CONFIRMED", "CORRECTED", "REJECTED", "DUPLICATE", name="verificationdecision"),
            nullable=False,
        ),
        sa.Column("verified_category", sa.String(length=64), nullable=True),
        sa.Column(
            "verified_severity",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="severitylevel_ver"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verifications_report_id", "verifications", ["report_id"])
    op.create_index("ix_verifications_reviewer_id", "verifications", ["reviewer_id"])

    # 7. Resolutions table
    op.create_table(
        "resolutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("resolver_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resolutions_issue_id", "resolutions", ["issue_id"])


def downgrade() -> None:
    op.drop_table("resolutions")
    op.drop_table("verifications")
    op.drop_table("ai_analyses")
    op.drop_table("model_versions")
    op.drop_table("evidences")
    op.drop_table("reports")
    op.drop_table("issues")
