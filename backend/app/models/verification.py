import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import SeverityLevel, VerificationDecision

if TYPE_CHECKING:
    from app.models.report import Report


class Verification(Base):
    """Human reviewer verdict on an AI prediction."""

    __tablename__ = "verifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    decision: Mapped[VerificationDecision] = mapped_column(
        SQLEnum(VerificationDecision), nullable=False
    )
    verified_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verified_severity: Mapped[SeverityLevel | None] = mapped_column(
        SQLEnum(SeverityLevel), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="verifications")
