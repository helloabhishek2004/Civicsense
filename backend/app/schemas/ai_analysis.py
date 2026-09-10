import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PriorityLevel, SeverityLevel
from app.schemas.model_version import ModelVersionRead


class AIAnalysisRead(BaseModel):
    """Schema for AI inference and decision engine results."""

    id: uuid.UUID
    report_id: uuid.UUID
    predicted_category: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    severity: SeverityLevel | None = None
    priority: PriorityLevel | None = None
    evidence_agreement: float | None = Field(None, ge=0.0, le=1.0)
    review_required: bool | None = None
    model_version: ModelVersionRead | None = None
    analysis_metadata: dict[str, Any] | None = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
