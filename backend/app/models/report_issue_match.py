"""Persistent record of report-to-issue similarity matching decisions.

Stores every AUTO_LINK and CANDIDATE match for audit, dedup review,
and approval/rejection workflows.
"""

import datetime
import uuid
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReportIssueMatch(Base):
    """Audit-trail entity for every report-to-issue scoring decision.

    Every report submission produces exactly one ReportIssueMatch row:
    - AUTO_LINK: report linked to existing issue (high confidence)
    - CANDIDATE: medium-confidence match, pending human review
    - NEW_ISSUE: no nearby match (score=0.0, no issue_id)
    """

    __tablename__ = "report_issue_matches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issue_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("issues.id", ondelete="SET NULL"), nullable=True, index=True
    )

    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)

    combined_score: Mapped[float] = mapped_column(Float, nullable=False)
    text_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    distance_meters: Mapped[float] = mapped_column(Float, nullable=False)
    category_match: Mapped[float] = mapped_column(Float, nullable=False)

    reasoning: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    embedding_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="similarity_matches")
    issue: Mapped["Issue | None"] = relationship("Issue", back_populates="similarity_matches")


# Avoid circular import at module level
from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.report import Report
