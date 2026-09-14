import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.report import Report
    from app.models.report_issue_match import ReportIssueMatch
    from app.models.resolution import Resolution


class Issue(Base):
    """Represents a real-world civic problem on the ground.

    Multiple citizen Reports can associate with one Issue over time.
    """

    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", index=True)
    primary_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    primary_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    report_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    text_embedding: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    embedding_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    image_embedding: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    vision_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Dynamic priority ranking (computed by priority engine)
    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    priority_level: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    priority_computed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    priority_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

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
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="issue")
    resolutions: Mapped[list["Resolution"]] = relationship(
        "Resolution", back_populates="issue", cascade="all, delete-orphan"
    )
    similarity_matches: Mapped[list["ReportIssueMatch"]] = relationship(
        "ReportIssueMatch", back_populates="issue"
    )
