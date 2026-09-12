import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AIJobStatus, AIProcessingStage

if TYPE_CHECKING:
    from app.models.report import Report


class AIJob(Base):
    """Tracks the execution of an AI pipeline job on a citizen report."""

    __tablename__ = "ai_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[AIJobStatus] = mapped_column(
        SQLEnum(AIJobStatus), default=AIJobStatus.QUEUED, nullable=False, index=True
    )
    current_stage: Mapped[AIProcessingStage] = mapped_column(
        SQLEnum(AIProcessingStage),
        default=AIProcessingStage.INTAKE_VALIDATION,
        nullable=False,
        index=True,
    )
    review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)

    queued_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    execution_mode: Mapped[str] = mapped_column(
        String(64), default="synchronous_demo", nullable=False
    )
    processor_name: Mapped[str] = mapped_column(
        String(128), default="Deterministic Demo Processor", nullable=False
    )
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="ai_jobs")
    events: Mapped[list["AIJobEvent"]] = relationship(
        "AIJobEvent",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="AIJobEvent.created_at",
    )


class AIJobEvent(Base):
    """Granular audit event recording each stage of the AI pipeline."""

    __tablename__ = "ai_job_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ai_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[AIProcessingStage] = mapped_column(SQLEnum(AIProcessingStage), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # STARTED, COMPLETED, FAILED
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
        index=True,
    )

    # Relationship
    job: Mapped["AIJob"] = relationship("AIJob", back_populates="events")
