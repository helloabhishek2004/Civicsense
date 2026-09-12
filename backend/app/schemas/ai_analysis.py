import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.enums import PriorityLevel, SeverityLevel
from app.schemas.common import ensure_utc
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

    @field_validator("created_at", mode="after")
    @classmethod
    def validate_utc(cls, v: datetime.datetime) -> datetime.datetime:
        res = ensure_utc(v)
        assert res is not None
        return res

    @field_serializer("created_at", when_used="json-unless-none")
    def serialize_utc(self, v: datetime.datetime) -> str:
        res = ensure_utc(v)
        assert res is not None
        return res.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)
