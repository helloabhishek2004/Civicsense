import datetime
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Uuid,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PriorityLevel, SeverityLevel

if TYPE_CHECKING:
    from app.models.model_version import ModelVersion
    from app.models.report import Report


class AIAnalysis(Base):
    """Server or edge AI analysis result associated with a report.

    Keeps confidence, severity, and priority strictly decoupled.
    """

    __tablename__ = "ai_analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Core AI outputs - strictly separated
    predicted_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[SeverityLevel | None] = mapped_column(SQLEnum(SeverityLevel), nullable=True)
    priority: Mapped[PriorityLevel | None] = mapped_column(SQLEnum(PriorityLevel), nullable=True)
    evidence_agreement: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    analysis_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="ai_analyses")
    model_version: Mapped[Optional["ModelVersion"]] = relationship(
        "ModelVersion", back_populates="ai_analyses"
    )
