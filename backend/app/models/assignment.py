import datetime
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AssignmentStatus, DepartmentRejectionReason

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.report import Report


class ReportAssignment(Base):
    """Immutable record representing a specific department dispatch/assignment attempt.

    Preserves audit history when a department accepts, completes, or declines a job.
    """

    __tablename__ = "report_assignments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department_name: Mapped[str] = mapped_column(String(64), nullable=False)
    assigned_by: Mapped[str] = mapped_column(String(128), nullable=False)
    assigned_to_officer: Mapped[str | None] = mapped_column(String(128), nullable=True)

    status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus),
        default=AssignmentStatus.ASSIGNED,
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[DepartmentRejectionReason | None] = mapped_column(
        SQLEnum(DepartmentRejectionReason), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="assignments")
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="assignments"
    )
