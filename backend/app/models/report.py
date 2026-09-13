import datetime
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PriorityLevel, ReportStatus

if TYPE_CHECKING:
    from app.models.ai_analysis import AIAnalysis
    from app.models.ai_job import AIJob
    from app.models.assignment import ReportAssignment
    from app.models.department import Department
    from app.models.evidence import Evidence
    from app.models.issue import Issue
    from app.models.report_issue_match import ReportIssueMatch
    from app.models.verification import Verification


class Report(Base):
    """Citizen-submitted civic defect report."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tracking_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    citizen_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    citizen_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    citizen_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    citizen_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    citizen_postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus),
        default=ReportStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address_hint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    issue_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("issues.id", ondelete="SET NULL"), nullable=True, index=True
    )

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    assigned_officer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    priority: Mapped[PriorityLevel | None] = mapped_column(
        SQLEnum(PriorityLevel), nullable=True, index=True
    )
    reassignment_required: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    edge_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    text_embedding: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    embedding_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    # Relationships
    issue: Mapped[Optional["Issue"]] = relationship("Issue", back_populates="reports")
    department_rel: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="reports"
    )
    assignments: Mapped[list["ReportAssignment"]] = relationship(
        "ReportAssignment",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="desc(ReportAssignment.created_at)",
    )
    evidences: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="report", cascade="all, delete-orphan"
    )
    ai_analyses: Mapped[list["AIAnalysis"]] = relationship(
        "AIAnalysis", back_populates="report", cascade="all, delete-orphan"
    )
    verifications: Mapped[list["Verification"]] = relationship(
        "Verification", back_populates="report", cascade="all, delete-orphan"
    )
    ai_jobs: Mapped[list["AIJob"]] = relationship(
        "AIJob", back_populates="report", cascade="all, delete-orphan"
    )
    similarity_matches: Mapped[list["ReportIssueMatch"]] = relationship(
        "ReportIssueMatch", back_populates="report", cascade="all, delete-orphan"
    )

    @property
    def current_assignment(self) -> Optional["ReportAssignment"]:
        """Return the latest assignment record if any exist."""
        return self.assignments[0] if self.assignments else None
