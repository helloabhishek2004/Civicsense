"""Add AI jobs, job events, and report operational assignment fields

Revision ID: 0002_ai_jobs_and_events
Revises: 0001_initial
Create Date: 2026-09-11 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_ai_jobs_and_events"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add operational fields to reports table
    op.add_column("reports", sa.Column("department", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("assigned_officer", sa.String(length=128), nullable=True))
    op.add_column(
        "reports",
        sa.Column(
            "priority",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="prioritylevel_report"),
            nullable=True,
        ),
    )
    op.create_index("ix_reports_department", "reports", ["department"])
    op.create_index("ix_reports_priority", "reports", ["priority"])

    # 2. Create ai_jobs table
    op.create_table(
        "ai_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("QUEUED", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED", name="aijobstatus"),
            nullable=False,
            server_default="QUEUED",
        ),
        sa.Column(
            "current_stage",
            sa.Enum(
                "INTAKE_VALIDATION",
                "PREPROCESSING",
                "VISION_ANALYSIS",
                "TEXT_ANALYSIS",
                "FUSION",
                "DECISION",
                "HUMAN_REVIEW",
                "COMPLETED",
                name="aiprocessingstage",
            ),
            nullable=False,
            server_default="INTAKE_VALIDATION",
        ),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("review_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("review_reason", sa.String(length=128), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("execution_mode", sa.String(length=64), nullable=False, server_default="synchronous_demo"),
        sa.Column("processor_name", sa.String(length=128), nullable=False, server_default="Deterministic Demo Processor"),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_jobs_report_id", "ai_jobs", ["report_id"])
    op.create_index("ix_ai_jobs_status", "ai_jobs", ["status"])
    op.create_index("ix_ai_jobs_current_stage", "ai_jobs", ["current_stage"])
    op.create_index("ix_ai_jobs_created_at", "ai_jobs", ["created_at"])

    # 3. Create ai_job_events table
    op.create_table(
        "ai_job_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column(
            "stage",
            sa.Enum(
                "INTAKE_VALIDATION",
                "PREPROCESSING",
                "VISION_ANALYSIS",
                "TEXT_ANALYSIS",
                "FUSION",
                "DECISION",
                "HUMAN_REVIEW",
                "COMPLETED",
                name="aiprocessingstage_event",
            ),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["ai_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_job_events_job_id", "ai_job_events", ["job_id"])
    op.create_index("ix_ai_job_events_report_id", "ai_job_events", ["report_id"])
    op.create_index("ix_ai_job_events_created_at", "ai_job_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_job_events")
    op.drop_table("ai_jobs")
    op.drop_index("ix_reports_priority", "reports")
    op.drop_index("ix_reports_department", "reports")
    op.drop_column("reports", "priority")
    op.drop_column("reports", "assigned_officer")
    op.drop_column("reports", "department")
